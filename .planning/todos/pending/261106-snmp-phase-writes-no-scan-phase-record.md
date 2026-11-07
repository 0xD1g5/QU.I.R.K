---
type: todo
created: 2026-11-06
title: SNMP phase writes no scan_phase_records row
source: Phase 235.3 research
priority: medium
area: run_scan.py (~:3026), quirk/scanner/snmp*
status: pending
resolves_phase: null
owner: null
---

# SNMP phase writes no scan_phase_records row

## Observed

The SNMP phase in `run_scan.py` (~:3026) is not wrapped by the phase-record helper, so it writes no
`scan_phase_records` row. A skipped or failed SNMP scan is indistinguishable from "not enabled" in coverage.

## Fix sketch

Wrap the SNMP phase in the same recorder used by the other connector phases and classify its outcome.

## Feasibility & Effort

Small. Mechanical wrap plus a coverage test; under half a plan.
