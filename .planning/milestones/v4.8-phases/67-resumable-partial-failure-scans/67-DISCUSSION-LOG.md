# Phase 67: Resumable / Partial-Failure Scans - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-14
**Phase:** 67-resumable-partial-failure-scans
**Areas discussed:** All four gray areas (user delegated all decisions to Claude)

---

## Checkpoint Persistence

| Option | Description | Selected |
|--------|-------------|----------|
| Incremental per-stage DB writes | After each stage completes, flush CryptoEndpoints to SQLite immediately. scan_checkpoints records which stages completed. Resume reads from DB. | ✓ |
| JSON serialization in checkpoint row | Keep bulk-at-end DB write; serialize each stage's endpoint list to a JSON blob in scan_checkpoints. | |
| Hybrid | Incremental writes + checkpoint table marks completion (same as option 1). | |

**User's choice:** Delegated to Claude — chose incremental per-stage DB writes.
**Notes:** Simpler than JSON serialization (no large blob handling), DB remains single source of truth, resume logic is straightforward (read existing rows, skip completed stages).

---

## Resume Scan Identifier

| Option | Description | Selected |
|--------|-------------|----------|
| scan_run_id (ISO timestamp) | Reuse the existing identifier from scan_jobs + CryptoEndpoint.scanned_at. No new ID type. | ✓ |
| New UUID | Generate a new UUID at scan start — simpler for humans to read. Requires new ID persistence. | |
| Auto-increment from scan_checkpoints | Use the checkpoint_id integer. Simplest but not stable across DB rebuilds. | |

**User's choice:** Delegated to Claude — chose scan_run_id for consistency with existing Phase 65/66 patterns.
**Notes:** Operators can find scan_run_id via `quirk scan --list-resumable` or the Phase 66 dashboard scan history page.

---

## Partial-Failure Panel (Dashboard)

| Option | Description | Selected |
|--------|-------------|----------|
| Executive Summary page card | Collapsible "Scanner Status" card, shown only when partial_failures is non-empty. Below score widgets, above Roadmap. | ✓ |
| Findings page section | Collapsible section above the findings table. | |
| Separate tab | New tab on the scan detail view. | |
| Always-shown summary | Show scanner status even for clean scans. | |

**User's choice:** Delegated to Claude — chose Executive Summary page, shown only when partial failures exist.
**Notes:** Executive Summary is the first page a consultant opens; partial failures are most actionable in that context. Clean-scan hiding reduces noise.

---

## Partial-Failure Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Structured reporting + wrap all scanners | Add partial_failures JSON array + migrate all inline try/except scanners to _wrapped_phase for uniform capture. | ✓ |
| Reporting only (no _wrapped_phase migration) | Only add the partial_failures array reporting; leave scanner invocation patterns unchanged. | |
| _wrapped_phase migration only | Migrate all scanners but defer structured output to Phase 68. | |

**User's choice:** Delegated to Claude — chose both: structured reporting AND _wrapped_phase migration.
**Notes:** The migration ensures all scanners produce errors via the same code path, which makes the partial_failures array comprehensive and consistent.

---

## Claude's Discretion

All four gray areas were delegated to Claude by the user ("let's move forward with Claude's recommended actions"). Key discretionary decisions:

- **Inventory phase persistence** — fingerprinting/target expansion endpoints persisted before first scanner stage begins (stage name: `inventory`)
- **Reports stage checkpointing** — reports stage also checkpointed; --resume can re-run reports without re-scanning
- **72-hour stale checkpoint warning** — stderr warning, non-blocking, for old checkpoints
- **Dashboard-launched scan resume excluded** — CLI only; Phase 65 stale-job recovery handles dashboard crashes
- **--list-resumable format** — rich.table.Table matching `quirk schedule list` style from Phase 63

## Deferred Ideas

- Dashboard-initiated scan resume — future UX phase
- Per-target checkpoint granularity — significantly more complex; stage-level sufficient for consulting use case
- Checkpoint auto-pruning (`quirk scan --clean-checkpoints`) — future housekeeping phase
- Scheduled scan resume — Phase 63 scheduled scans could inherit resume; deferred pending stable checkpoint infrastructure
