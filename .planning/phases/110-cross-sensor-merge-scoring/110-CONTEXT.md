# Phase 110: Cross-Sensor Merge & Scoring - Context

**Gathered:** 2026-05-25
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase delivers the **cross-sensor merge**: a consultant runs `quirk sensor merge` and the
console produces **one canonical CBOM and one quantum-readiness score** from the union of all
pushed sensor endpoints — using **Option A** (union of findings re-run through the existing
`build_evidence_summary()` → `compute_readiness_score()` → `build_cbom()` engines, unmodified in
spirit). The merge emits an explicit `coverage_warning` when any enrolled sensor is overdue, never
silently presenting partial data as complete. The same RFC1918 `host:port` reported by two sensors
in different segments must yield **two distinct CBOM components** (keyed by `sensor_id`).

**Out of scope (downstream):** dashboard rendering of the registry / per-segment filters / coverage
banner (Phase 111); chaos-lab physical reproduction of the two-segment scenario (Phase 112, LAB-02).
Automatic merge triggering (poll-on-full-check-in) is v5.5 (D-06) — merge stays manual; the
`merge_scan()` function is built as a standalone callable so v5.5 can invoke it without refactoring.

</domain>

<decisions>
## Implementation Decisions

### Pre-locked from Phase 106 architecture (carried forward — do NOT re-litigate)
- **(D-01) Option A scoring:** the merged score = union of all sensor findings re-run through the
  existing `compute_readiness_score()` engine, **unchanged**. NEVER a weighted-average or
  weakest-link of pre-scored per-segment results (averaging pre-scored sub-results is
  mathematically wrong — ratio penalties use full-population denominators).
- **(D-03) Component identity:** the CBOM Pass-1 component identity must include `sensor_id`, so the
  same RFC1918 `host:port` in two segments produces two distinct components, not one merged entry.
- **(D-06) Manual merge:** `quirk sensor merge` is operator-invoked; `merge_scan()` is a standalone
  callable seam (no poller/scheduler state built in v5.4).
- **(D-14) Coverage & staleness:** a sensor is **overdue** when `now > last_push_at + 2×cadence`
  (never-pushed enrolled sensor is also overdue); merge emits `coverage_warning` listing overdue
  `sensor_id`s (null when all current). Partial coverage **is scored but always flagged** — never
  silently merged as complete. Scan results flagged **stale after 30 days**. All thresholds
  operator-overridable.

### Union Assembly & Merge Scope
- **Union definition:** each enrolled sensor's **most-recent push** + the local (NULL `sensor_id`)
  rows. A re-push supersedes the sensor's prior data (latest-per-`sensor_id` by max `scanned_at`).
- **`merge_scan(db, ...) -> result`** is a standalone callable; the `quirk sensor merge` CLI is a
  thin wrapper over it (D-06 v5.5 auto-trigger seam).
- **Scope:** all enrolled sensors by default; a `--segment` subset filter is deferred.

### CBOM Component Identity (MERGE-03)
- **Minimal `builder.py` change:** include `sensor_id` in the cert/host `bom_ref` derivation when
  present — `crypto/certificate/{sensor_id}:{host}:{port}` (and the analogous host-component ref).
  This is the **sanctioned minimal identity-key change** mandated by D-03, NOT a fork or
  re-implementation of the scoring/CBOM logic (MERGE-01's "not modified" forbids forking the
  engine, not threading a discriminator into the identity key).
- **Backward-compat:** a **NULL `sensor_id`** (implicit local single-host scan) keeps the current
  `crypto/certificate/{host}:{port}` bom_ref — existing single-host scans are unchanged.

### Coverage Warning (MERGE-04)
- **Shape:** the score JSON gains `coverage_warning`: **`null`** when all enrolled sensors are
  current, else an object `{missing_sensors: [sensor_id, ...], reason: <str>}`.
- Overdue/stale rules per D-14 (above). Partial coverage is scored but the warning is always present.

### Merged Result Persistence (MERGE-05)
- **New merged `scan_id`** = an ISO-timestamp at merge execution time.
- Persisted as a **normal scan result** so the dashboard and report renderers consume it unchanged
  (Phase 111 reads it).
- **`scanned_at` preservation:** endpoints keep their **sensor-local `scanned_at`**; only the
  scan-result envelope carries the merge timestamp — the merge command does NOT rewrite per-endpoint
  timestamps to its own execution time.
- **CLI output:** print the merged `scan_id` + the score + a `coverage_warning` summary.

### Claude's Discretion
- Exact `merge_scan()` parameter list and return type; how the merged result rows are written
  (reusing the existing scan-result persistence path).
- The precise SQL/ORM query for "latest push per sensor_id".
- `coverage_warning.reason` wording and whether per-sensor overdue detail is included.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets (the engines — reuse, do NOT fork)
- `quirk/intelligence/evidence.py::build_evidence_summary` — evidence rollup over endpoints.
- `quirk/intelligence/scoring.py::compute_readiness_score` — the Option A scoring engine.
- `quirk/cbom/builder.py::build_cbom(endpoints: list[CryptoEndpoint]) -> Bom` — Pass-1 algorithm
  dedup + cert/host components. **Identity note:** today `cert_bom_ref = f"crypto/certificate/{ep.host}:{ep.port}"`
  (builder.py ~L697) does NOT include `sensor_id` — this is the exact line set that the minimal
  D-03 change targets so two segments don't collapse.
- `quirk/models.py` — `CryptoEndpoint` (has `sensor_id`, `segment` from Phase 107), `Sensor`
  (`last_push_at`, `expected_cadence_minutes`), `SensorPush`.
- The Phase 109 `_ingest_envelope` persists `CryptoEndpoint` rows tagged with `sensor_id`/`segment`
  — those are the rows the union query reads.

### Established Patterns
- `run_scan.py` scan-result persistence (`scan_id` / `scanned_at` handling ~L930-990) — the merged
  result should be written via the same path so it appears as a normal scan.
- CLI dispatch: `run_scan.py:main()` argv switch → `quirk/cli/sensor_cmd.py::run_sensor` (Phase 108);
  add a `merge` subcommand there.

### Integration Points
- `quirk sensor merge` extends the existing `quirk/cli/sensor_cmd.py` sensor subparser.
- The merged score JSON is what Phase 111's dashboard `coverage_warning` banner will read.

</code_context>

<specifics>
## Specific Ideas

- The single most important invariant: the merged score is Option A (union through the unmodified
  engine), provable by a test, and the same `host:port` in two segments yields two CBOM components
  (MERGE-03 regression test).
- `scanned_at` must be preserved per-endpoint (MERGE-05) — a merge is an aggregation, not a re-scan.

</specifics>

<deferred>
## Deferred Ideas

- `--segment` subset merge filter (default is all enrolled sensors).
- Automatic merge trigger / poller (v5.5, D-06).
- Physical two-segment reproduction of MERGE-03 in the chaos lab (Phase 112, LAB-02).

## FLAGGED FOR RESEARCH/PLANNING

- **MERGE-01 ("engines not forked or modified") vs D-03 ("identity must include sensor_id").**
  Confirm the chosen path — a minimal `bom_ref` identity-key change in `builder.py` (accepted
  default) vs pre-namespacing host keys before `build_cbom` so the engine is literally untouched.
  Determine which best satisfies BOTH the letter of MERGE-01 and D-03, and whether the minimal
  builder change risks any regression to existing single-host CBOM output (it must not — NULL
  `sensor_id` keeps the current ref). Produce a regression test proving two-segment same-IP →
  two components AND that single-host output is byte-stable.

</deferred>
