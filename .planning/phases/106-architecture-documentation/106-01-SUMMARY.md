---
phase: 106-architecture-documentation
plan: 01
subsystem: infra
tags: [architecture, distributed-scanner, wire-contract, mermaid, documentation]

# Dependency graph
requires: []
provides:
  - "Canonical v5.4 distributed-scanner architecture contract (docs/architecture-distributed.md)"
  - "Wire payload schema (payload_id/pushed_at/received_at/schema_version/sensor_version) for Phase 107 sensor_pushes + Phase 108/109 wire format"
  - "Additive data-model keying (sensor_id, host, port) for Phase 107 CryptoEndpoint columns"
  - "Enrollment/auth + ingest dedup/replay/body-size policy for Phase 109 ingest route"
  - "Merge pipeline + Option A scoring contract for Phase 110 merge_scan()"
  - "Forbidden-additions violation reference + Windows floor/ceiling scope"
affects: [107-data-model, 108-sensor-winci, 109-ingestion, 110-merge, 111-dashboard, 112-chaos-lab-stab]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Sensor/console split within one package via run_scan.py subcommand dispatch (no package split)"
    - "Identical wire payload for HTTPS push and air-gap export/import (push-to-file)"
    - "Transport-conditional replay window (HTTPS-only) with payload-conditional dedup"

key-files:
  created:
    - "docs/architecture-distributed.md"
  modified: []

key-decisions:
  - "Documentation-only phase: zero runtime code shipped, single Markdown deliverable"
  - "Option A unified scoring locked (union re-scored, never average pre-scored sub-results)"
  - "One-time-use SHA-256-hashed enrollment tokens, not time-windowed"
  - "(sensor_id, host, port) uniqueness key with NULL sensor_id = implicit local sensor"
  - "Windows v5.4 = floor-in (OS-agnostic, POSIX audit, windows-latest hard gate) / ceiling -> v5.5"

patterns-established:
  - "All downstream phases cite this doc by section number as their design contract"
  - "Code seams cited by file + symbol name (verified against repo), not blind line number"

requirements-completed: [ARCH-01, ARCH-02, ARCH-03, ARCH-04]

# Metrics
duration: 2min
completed: 2026-05-25
---

# Phase 106 Plan 01: Distributed Scanner Architecture Documentation Summary

**Canonical v5.4 sensor/console architecture contract locking the wire payload schema, additive (sensor_id, host, port) data-model keying, the three committed PM decisions, the forbidden-additions list, and the Windows floor/ceiling scope across 10 sections plus two Mermaid diagrams.**

## Performance

- **Duration:** 2 min
- **Started:** 2026-05-25T16:37:12Z
- **Completed:** 2026-05-25T16:39:14Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- Authored `docs/architecture-distributed.md` (395 lines) with all 10 locked sections in order.
- Specified the complete wire contract: field table + JSON example covering payload_id, pushed_at, received_at, schema_version, sensor_version; HMAC-SHA256 `X-Sensor-Signature`; zstd-level-3 + httpx transport; air-gap export/import identical-payload carve-out.
- Committed the ingest dedup/replay/DoS policy: payload_id dedup -> 409, ±15-min HTTPS-only replay window echoing console_utc, 10 MB body limit -> 413, indefinite retention, `extra='ignore'` warn-only version-skew.
- Locked the additive data-model (nullable sensor_id + segment on CryptoEndpoint, NULL = implicit local, CBOM Pass-1 identity must include sensor_id) and the enrollment manifest field set.
- Recorded the merge pipeline (manual `quirk sensor merge`, standalone `merge_scan()`, Option A scoring through the unchanged engine chain, coverage_warning/staleness thresholds) and the three PM decisions, full forbidden list, and Windows scope.
- Two Mermaid diagrams (topology flowchart + push sequenceDiagram) that render in GitHub/Obsidian.

## Task Commits

Each task was committed atomically:

1. **Task 1: Author core architecture sections (1–7)** - `bec2136` (docs)
2. **Task 2: Author decision-lock sections (8–10)** - `ceaacec` (docs)

**Plan metadata:** see final docs commit below.

## Files Created/Modified
- `docs/architecture-distributed.md` - Canonical v5.4 distributed-scanner architecture contract; 10 locked sections + two Mermaid diagrams.

## Decisions Made
None beyond the plan — all content derived verbatim from 106-CONTEXT.md decisions D-01..D-15. Code seams (CryptoEndpoint L9, IntegrationDelivery L245, compute_readiness_score L119 / `/1.5` rollup L290, build_cbom L445 / algo_registry L461, require_auth L34 / compare_digest L54/L61, token_urlsafe L100, scheduler POSIX-isms L136/L258, _ensure_columns L127 / _ADDITIVE_MIGRATIONS L172, run_scan dispatch ~L381) were confirmed against the live repo before citation, then cited by symbol name.

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 107 (data-model) can proceed: §3 wire schema and §5 data-model keying are fully specified.
- All four requirements (ARCH-01..04) satisfied and grep-verified.
- No blockers.

## Self-Check: PASSED

---
*Phase: 106-architecture-documentation*
*Completed: 2026-05-25*
