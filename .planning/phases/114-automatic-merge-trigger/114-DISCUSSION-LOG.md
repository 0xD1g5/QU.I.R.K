# Phase 114: Automatic Merge Trigger - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-26
**Phase:** 114-automatic-merge-trigger
**Areas discussed:** Trigger mechanism, "All sensors in" + double-fire, Config shape & default, Failure surfacing

---

## Trigger mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| BackgroundTask (async) | FastAPI BackgroundTasks — push returns immediately, merge_scan() runs after response; merge failure decoupled from push transaction. | ✓ |
| Inline after commit (sync) | merge_scan() synchronously at end of sensor_push() after commit; simpler/deterministic but last push waits for full merge. | |
| Separate poller | Background loop/thread checking "all sensors in"; more moving parts, no existing in-process scheduler. | |

**User's choice:** BackgroundTask (async)
**Notes:** Task must open its own DB session (request-scoped session closes after response) and resolve its own output_dir — captured as D-02. Best structural fit for SC#3 failure-isolation.

---

## "All sensors in" + double-fire guard

| Option | Description | Selected |
|--------|-------------|----------|
| New push since last merge | All non-revoked sensors have last_push_at AND ≥1 push newer than last MergeRun.merged_at. Handles daily re-runs, avoids stale re-merges. | ✓ |
| All have ever pushed | Trigger whenever every sensor has non-null last_push_at; re-fires on every push once complete, needs separate debounce. | |
| Within cadence window | Trigger when all sensors pushed inside expected_cadence_minutes window. | |

**User's choice (condition):** New push since last merge

| Option | Description | Selected |
|--------|-------------|----------|
| Idempotent re-check in task | Task re-evaluates "push newer than latest MergeRun?" as final gate; second task no-ops. No lock. | ✓ |
| DB merge-lock row | Atomic claim of a lock row/column; strongest guarantee but adds schema + crash-release handling. | |
| Debounce window | Coalesce triggers over a fixed delay; smooths bursts but timing-tuning + fuzzy to test. | |

**User's choice (race guard):** Idempotent re-check in task
**Notes:** Residual TOCTOU window accepted for single-tenant v5.5 — a duplicate MergeRun is harmless (D-06).

---

## Config shape & default

| Option | Description | Selected |
|--------|-------------|----------|
| ON by default | Matches phase goal (eliminate mandatory manual step for common case); operators disable for explicit control. | ✓ |
| OFF by default | Preserves exact v5.4 behavior unless enabled; works against the phase goal. | |

**User's choice (default):** ON by default

| Option | Description | Selected |
|--------|-------------|----------|
| Ship all-in only; config-extensible | Implement new-push-since-last-merge now; structure config for later cadence add. | |
| Ship both conditions now | Implement all-sensors-in AND cadence-window selectable from config in this phase. | ✓ |

**User's choice (trigger options):** Ship both conditions now

| Option | Description | Selected |
|--------|-------------|----------|
| Push-evaluated time window | cadence-window stays push-driven: a push triggers merge when time since last MergeRun exceeds the window; merges what's arrived + coverage_warning. No timer. | ✓ |
| Standalone scheduler/poller | Real background timer firing merges every N min; conflicts with "no new heavy infra". | |
| External cron + existing CLI | Document cron of `quirk sensor merge`; only ship all-sensors-in in-process. | |

**User's choice (cadence semantics):** Push-evaluated time window
**Notes:** Both trigger modes are push-evaluated — no scheduler thread, honors "no new heavy infra".

---

## Failure surfacing

| Option | Description | Selected |
|--------|-------------|----------|
| IntegrationDelivery audit row + log | Reuse push-path audit pattern (destination "auto_merge", status "failed", safe_str summary) + warning log; queryable, dashboard/registry already read these rows; no new storage. | ✓ |
| Audit row + dashboard banner | Above plus a visible dashboard banner; better visibility but adds React/UI work to scope. | |
| Log-only | logger.warning/error only; invisible unless operator reads logs. | |

**User's choice:** IntegrationDelivery audit row + log
**Notes:** Satisfies SC#3 "surfaced to the operator" with zero UI work this phase.

---

## Claude's Discretion

- Exact config key paths/names for the enable flag and `trigger_condition` selector.
- Exact background-task DB session + output_dir wiring (mirror `_cmd_merge`).
- Whether a successful auto-merge writes an `ok` IntegrationDelivery row + exact strings.
- Optional surfacing of "last auto-merge result" in the registry response.
- How the cadence-window minutes are resolved (reuse `expected_cadence_minutes` vs dedicated key).

## Deferred Ideas

- Standalone scheduler/poller for true time-based cadence — rejected for v5.5 (no new heavy infra).
- Dashboard banner / React indicator for auto-merge health — out of scope; candidate for a UI phase.
- DB merge-lock row / advisory lock for hard double-merge guarantee — not needed on single-tenant.
- External cron + `quirk sensor merge` for cadence — available to operators, not the chosen in-product path.
