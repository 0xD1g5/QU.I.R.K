---
type: todo
created: 2026-11-06
title: Merged sensor score ignores connector coverage skips
source: Phase 235.3 research (P-05 known limitation)
priority: medium
area: quirk/sensor/*, quirk/dashboard/api/routes/sensor*, quirk/intelligence/scoring*
status: pending
resolves_phase: null
owner: null
---

# Merged sensor score ignores connector coverage skips

## Observed

Sensor push filters the coverage-skip ADVISORY rows, and `scan_phase_records` are not pushed. A connector a
sensor skipped (missing extra, refused target, no credentials) therefore does not lower the merged score on the
console. Same limitation 235.1 accepted for `missing_binary`.

## Fix sketch

Push `scan_phase_records` (or the coverage-skip advisory rows) with the sensor payload and have the merge feed
`COVERAGE_SKIP_ADVISORY_CATEGORIES` into the merged scoring input.

## Feasibility & Effort

Medium. Needs a sensor payload schema addition (versioned, backward compatible) plus merge-side scoring wiring;
the scoring side already exists (235.3-09). Roughly 1 plan.

## Confirmed and widened (v5.28.2 milestone audit, 2026-11-09)

Confirmed in code: `quirk/cli/sensor_cmd.py:598` filters the coverage-skip advisory rows out of the push. Also,
`scan_phase_records` are never pushed. A sensor-sourced scan therefore has no phase records on the server, so
its Scan Coverage chips and its Data at Rest / Identity / Motion empty states fall back to the static text
instead of the recorded skip reason. The fix should push the phase records as well as the advisory rows.
