# Phase 67: Resumable / Partial-Failure Scans - Context

**Gathered:** 2026-05-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 67 adds two capabilities to the CLI scan pipeline:

1. **Resumable scans** — a crash between scanner stages leaves a recoverable `scan_checkpoints` SQLite row; `quirk scan --resume <scan_run_id>` continues from the last completed stage, producing results indistinguishable from an uninterrupted run.
2. **Structured partial-failure reporting** — a single scanner failure (missing cloud credentials, unreachable host, missing optional extra) no longer silently swallows partial results; instead it produces a `partial_failures` array in the output JSON and a per-scanner status panel in the dashboard.

**In scope:** `scan_checkpoints` SQLite table, per-stage incremental DB persistence, `quirk scan --resume <scan_run_id>` CLI flag, `quirk scan --list-resumable` listing, `partial_failures` JSON array in run stats, uniform `_wrapped_phase` coverage for all scanner stages, dashboard "Scanner Status" card on Executive Summary page.

**Out of scope:** Dashboard-initiated scan resume (Phase 65 stale-job recovery covers dashboard crashes — CLI-only for this phase), per-target checkpoint granularity (stage-level only), scan deletion or checkpoint pruning UI.

</domain>

<decisions>
## Implementation Decisions

### D-01: Checkpoint Persistence — Incremental Per-Stage DB Writes

Change the scan from bulk-at-end persistence to **incremental per-stage commits**. After each scanner stage completes (TLS, SSH, API, identity, data_at_rest, broker/email), flush that stage's `CryptoEndpoint` rows to SQLite immediately using `get_session()` before moving to the next stage. Write a `scan_checkpoints` row marking the stage complete.

This means:
- The `scan_checkpoints` table only records **which stages completed and when** — it does NOT serialize endpoint data (the DB already has it).
- Resume reads the DB for completed-stage endpoints and skips those stages.
- The inventory/fingerprinting phase endpoints (already accumulated before TLS/SSH) must be persisted before the first scanner stage begins.

`scan_checkpoints` table schema (new SQLAlchemy model in `quirk/models.py`, registered via `_ensure_scan_checkpoints_table(engine)` in `quirk/db.py:init_db()`):

| Column | Type | Notes |
|---|---|---|
| `checkpoint_id` | `Integer` PK autoincrement | |
| `scan_run_id` | `String` indexed | ISO timestamp — same as `CryptoEndpoint.scanned_at` / `scan_jobs.scan_run_id` |
| `stage` | `String(32)` | `inventory` / `tls` / `ssh` / `api` / `identity` / `data_at_rest` / `broker_email` / `reports` |
| `status` | `String(16)` | `completed` / `partial` / `failed` / `skipped` |
| `completed_at` | `DateTime` | UTC timestamp when stage finished |
| `endpoint_count` | `Integer` | Number of `CryptoEndpoint` rows persisted for this stage |
| `partial_failure` | `Boolean` | True if stage completed but had scanner-level errors |
| `error_summary` | `Text` nullable | JSON array of `{scanner, error_category, error_message}` entries from `error_endpoints` for this stage |

Registration: add `_ensure_scan_checkpoints_table(engine)` to `init_db()` in `quirk/db.py` after `_ensure_scan_jobs_table(engine)`, using the same `Base.metadata.create_all(engine, checkfirst=True)` pattern from Phase 65.

### D-02: Resume Scan Identifier — scan_run_id (ISO Timestamp)

`quirk scan --resume <scan_run_id>` uses the **same ISO timestamp identifier** already used by `scan_jobs.scan_run_id`, `CryptoEndpoint.scanned_at`, and the Phase 65/66 dashboard APIs. No new identifier type.

Operators find resumable scan IDs via:
- `quirk scan --list-resumable` — lists `scan_checkpoints` rows where the stage sequence is incomplete (not all expected stages have `status=completed`). Displays: scan_run_id, last completed stage, elapsed time since crash.
- The Phase 66 dashboard `/scans` history page (scan_run_id is the scan identifier there).

Resume flow in `run_scan.py`:
1. Load `scan_checkpoints` rows for the given `scan_run_id`.
2. Determine which stages are already `completed` or `partial`.
3. Load existing `CryptoEndpoint` rows for that `scan_run_id` from the DB (these are the accumulated results so far).
4. Skip completed stages; re-run failed or incomplete stages from the checkpoint onward.
5. At the end, write a final complete `scan_checkpoints` entry with `stage="reports"`.

**Stale checkpoint warning:** if `completed_at` of the last checkpoint is > 72 hours ago, print a stderr warning: `[warn] checkpoint is N hours old — re-running may produce different results than a fresh scan.` Do NOT auto-delete or block the resume.

### D-03: Partial-Failure Surface — JSON Array + Executive Page Panel

Two surfaces for RESUME-02:

**1. `partial_failures` in run_stats / output JSON:**
Add a `partial_failures` key to `run_stats` (and to the output JSON / dashboard `/api/scan/latest`). Schema:
```json
"partial_failures": [
  {
    "stage": "identity",
    "scanner": "gcp_connector",
    "error_category": "missing_extra",
    "error_message": "optional extra [cloud] not installed",
    "endpoint_count": 0
  }
]
```
Source: the `error_endpoints` list accumulated by `_wrapped_phase` and `_emit_missing_extra_advisory`.

**2. Dashboard "Scanner Status" card:**
Add a collapsible "Scanner Status" card to the **Executive Summary page** (`src/dashboard/src/pages/executive.tsx`). Rules:
- **Only shown when `partial_failures` is non-empty** (hidden for clean scans).
- Each row: scanner label, status badge (`Partial` / `Failed` / `Skipped`), error category, one-line error message.
- The card appears below the existing score/readiness widgets, above the Roadmap section.
- Data sourced from `GET /api/scan/latest` (extend `ScanLatestResponse` with `partial_failures[]`).

### D-04: Partial-Failure Scope — Migrate All Scanners to _wrapped_phase

ALL scanner invocations that currently use **inline try/except** blocks should be migrated to `_wrapped_phase` for consistent error capture and uniform `partial_failures` reporting:
- Currently wrapped: TLS phase (`_run_tls_phase`), SSH phase (`_run_ssh_phase`), broker phase (`_run_broker_phase`)
- Must be wrapped: JWT (`scan_jwt_targets`), container (`scan_container_targets`), source (`scan_source_targets`), AWS (`scan_aws_targets`), Azure (`scan_azure_targets`), GCP (`scan_gcp_targets`), kerberos/SAML/DNSSEC identity scanners, database (`scan_database_targets`), email (`scan_email_targets`)

The migration is: replace inline `try/except` + conditional execution with a `_wrapped_phase(run_stats, stage_name, scanner_label, fn, error_endpoints, logger)` call. Since `_wrapped_phase` already handles `missing_extra` advisories via `error_endpoints`, the existing `_emit_missing_extra_advisory` calls are still valid — `_wrapped_phase` adds crash protection on top.

Group related scanners into a single stage for checkpointing purposes (e.g., JWT + container + source → `api` stage; AWS + Azure + GCP + cloud DB + identity → `identity` stage). This matches the existing `update_job_stage()` stage names.

### Claude's Discretion

- **Inventory phase persistence:** Fingerprinting and target expansion results (the `inventory_endpoints` list) are persisted before the first scanner stage begins — checkpoint stage name `inventory`. This ensures that even if TLS crashes immediately, the discovered targets are saved.
- **Reports stage checkpointing:** The `reports` stage (write_reports, CBOM output) is also checkpointed. If it crashed, `--resume` re-runs reports on the existing complete endpoint set without re-scanning anything.
- **`--list-resumable` format:** tabular output via `rich.table.Table` — columns: Scan ID, Last Stage, Stage Status, Time Since Crash, Target (if recoverable from `scan_jobs`). Uses existing `quirk.logging_util.Logger`.
- **Dashboard panel component:** Use shadcn/ui `Card` + `Badge` (already in the project) — same pattern as the existing findings severity badges. No new UI dependencies.
- **`partial_failures` on `/api/scan/latest`:** Add as an optional field to `ScanLatestResponse` in `quirk/dashboard/api/schemas.py`. Empty list `[]` for fully-successful scans (never null).
- **Checkpoint cleanup:** No auto-cleanup. Manual only (out of scope for this phase).
- **Dashboard-launched scan resume:** Phase 65 stale-job recovery (`_recover_stale_jobs`) already handles dashboard job crashes by flipping `status → failed`. Phase 67 does NOT add resume capability for dashboard-launched scans — CLI only.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase Requirements
- `.planning/REQUIREMENTS.md` §RESUME-01, §RESUME-02 — exact acceptance criteria
- `.planning/ROADMAP.md` §Phase 67 — goal statement, success criteria

### Core Scan Pipeline (PRIMARY — read before planning)
- `run_scan.py` — full scanner stage sequence; `_wrapped_phase` (lines 113–141), `error_endpoints` accumulation, `update_job_stage()` calls at each stage boundary, bulk-at-end DB persist pattern (the pattern this phase changes)
- `run_scan.py` — stage names already used by Phase 65: `discovery`, `tls`, `ssh`, `api`, `identity`, `data_at_rest`, `reports` — checkpointing must use the same names

### Database and ORM Patterns
- `quirk/models.py` — SQLAlchemy declarative pattern; `ScanJob` model (Phase 65) is the closest analog for the new `ScanCheckpoint` model
- `quirk/db.py` — `init_db()`, `get_session()`, `_ensure_scan_jobs_table(engine)` pattern (Phase 65); new `_ensure_scan_checkpoints_table(engine)` follows identically

### Phase 65 scan_jobs Pattern (PRIMARY analog for scan_checkpoints)
- `.planning/phases/65-dashboard-initiated-scan/65-CONTEXT.md` §D-02 — `scan_jobs` table schema; `scan_run_id` column is the same identifier used here; `_ensure_scan_jobs_table` registration pattern
- `.planning/phases/65-dashboard-initiated-scan/65-CONTEXT.md` §D-12 — `_recover_stale_jobs` stale-job recovery — Phase 67 does NOT duplicate this; dashboard jobs stay under Phase 65's recovery mechanism
- `quirk/cli/job_progress.py` — `update_job_stage()` writes to `scan_jobs`; the new checkpoint write helper (`write_scan_checkpoint()`) follows the same lightweight DB-open-write-close pattern

### Dashboard API
- `quirk/dashboard/api/routes/scan.py` — `get_latest_scan()` route + `ScanLatestResponse` shape; extend with `partial_failures: list[PartialFailureEntry]`
- `quirk/dashboard/api/schemas.py` — `ScanLatestResponse` (extend); add `PartialFailureEntry` Pydantic model
- `quirk/dashboard/api/middleware/auth.py` — `require_auth` dependency (GET route, no CSRF needed)

### Phase 65 Auth Pattern
- `.planning/phases/65-dashboard-initiated-scan/65-CONTEXT.md` §D-10 — read-only GET routes require only `require_auth`; no new auth wiring needed for the dashboard panel (it's data from an existing endpoint)

### Phase 62 Hook Cancellation Pattern
- `.planning/phases/62-react-hook-cancellation-pattern/62-CONTEXT.md` — any new React hooks for the scanner status panel MUST follow `let cancelled = false` + `return () => { cancelled = true }`

### Frontend Patterns
- `src/dashboard/src/pages/executive.tsx` — add the "Scanner Status" card here; reference existing card layout for placement
- `src/dashboard/src/components/ui/` — shadcn/ui `Card`, `Badge` components (already used for severity badges in findings)
- `src/dashboard/src/types/api.ts` — add `PartialFailureEntry` TypeScript interface; extend `ScanLatestResponse` type

### Feedback Constraints (MANDATORY)
- Dashboard build step: after any `.tsx` edits, run `npm run build` in `src/dashboard/` before testing — statics are pre-built, FastAPI does not hot-reload them

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `run_scan.py::_wrapped_phase()` (lines 113–141) — already catches BaseException per stage, records error CryptoEndpoints; Phase 67 wraps remaining inline scanners with this to ensure uniform error capture
- `quirk/cli/job_progress.py::update_job_stage()` — lightweight DB write helper (open session → update row → close); `write_scan_checkpoint()` follows the exact same pattern
- `quirk/models.py::ScanJob` — direct structural analog for the new `ScanCheckpoint` model; same `scan_run_id` linkage, same `_ensure_*_table()` registration
- `src/dashboard/src/components/ui/badge.tsx` — `Badge variant="destructive"` (red) / `"secondary"` (gray) already used in findings table; reuse for partial/failed/skipped status badges

### Established Patterns
- **Scan stage names:** `discovery`, `tls`, `ssh`, `api`, `identity`, `data_at_rest`, `reports` — defined by Phase 65 `update_job_stage()` calls; checkpoint stage names MUST match
- **`scan_run_id` = ISO timestamp:** `run_stats["started_utc"]` at line ~452 of `run_scan.py`; this is the `scanned_at` value for all `CryptoEndpoint` rows in a scan, and the `scan_jobs.scan_run_id` from Phase 65
- **`init_db()` registration chain:** add `_ensure_scan_checkpoints_table(engine)` after `_ensure_scan_jobs_table(engine)` — follows the established pattern for each new table
- **Optional GET data fields:** `partial_failures` on `ScanLatestResponse` uses `Optional[list[PartialFailureEntry]] = []` — additive schema change that doesn't break existing consumers

### Integration Points
- `run_scan.py` lines ~640–1143 — the scanner stage execution block; this is where per-stage checkpoint writes and `_wrapped_phase` migrations happen
- `quirk/db.py::init_db()` — register new `ScanCheckpoint` table here
- `quirk/dashboard/api/routes/scan.py::get_latest_scan()` — extend to include `partial_failures` from `error_endpoints` stored in checkpoint `error_summary` JSON
- `src/dashboard/src/pages/executive.tsx` — insert "Scanner Status" card component; only render when `data.partial_failures?.length > 0`

</code_context>

<specifics>
## Specific Ideas

- `quirk scan --list-resumable` output should use `rich.table.Table` — same visual style as `quirk schedule list` from Phase 63. Columns: Scan ID, Last Completed Stage, Status, Age, Target (if available from `scan_jobs` join).
- The `partial_failures` key must appear in the **output JSON** (`reports/writer.py` run_stats section) AND in the **dashboard API** (`/api/scan/latest`). These are two separate surfaces — plan tasks for both.
- The "Scanner Status" card on Executive Summary uses the same amber/red/gray color language as existing severity badges. Status text: `Partial` (amber), `Failed` (red), `Skipped` (gray — missing optional extra). `Completed` stages are NOT shown (card only appears when there's something to report).
- Finding identity for `_wrapped_phase` migration: stages that use multiple scanner functions (e.g., `api` stage = jwt + container + source) should call each scanner via a separate `_wrapped_phase` call with its own `scanner_label`, feeding into the same stage's `error_endpoints`. The stage checkpoint aggregates all three.
- The 72-hour stale checkpoint warning is stderr-only (no blocking). The format: `[warn] scan checkpoint for {scan_run_id} is {N}h old — verify targets are still valid before resuming.` Uses `logger.warn()`.

</specifics>

<deferred>
## Deferred Ideas

- **Dashboard-initiated scan resume** — `quirk serve` restart already flips running jobs to `failed` (Phase 65 D-12 stale-job recovery); resuming dashboard-launched scans from the UI is a future UX phase
- **Per-target checkpoint granularity** — checkpointing at the individual target level (not just stage level) would allow resuming a partially-completed TLS stage; deferred as significantly more complex than stage-level checkpointing
- **Checkpoint auto-pruning** — a `quirk scan --clean-checkpoints [--older-than N]` command; deferred to a future housekeeping phase
- **Scheduled scan resume** — Phase 63 scheduled scans could inherit resume capability; deferred pending Phase 67 stable checkpoint infrastructure

None — discussion stayed within phase scope (user delegated all decisions to Claude).

</deferred>

---

*Phase: 67-resumable-partial-failure-scans*
*Context gathered: 2026-05-14*
