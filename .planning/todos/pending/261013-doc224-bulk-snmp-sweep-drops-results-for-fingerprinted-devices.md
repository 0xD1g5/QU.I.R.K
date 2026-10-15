---
type: todo
created: 2026-10-13
source: Phase 224 GC3-R3 (part 05, docs/report-interpretation.md §10.3 SNMP em-dash row)
priority: medium
area: run_scan.py (bulk SNMP sweep result application)
status: pending
resolves_phase: null
owner: "999.130"
---

# Bulk SNMP sweep probes identified devices but discards the answer, so the SNMP column shows an em-dash

With `enable_snmp` on, the sweep probes every TLS/SSH/PQC host (`run_scan.py:2994` `_scan_snmp_targets(`), but it
applies a result only to devices whose vendor is still `Unknown` (`run_scan.py:3026`). Even those mutations land on
detached rows that are not persisted (in-code "KNOWN PRE-EXISTING GAP" comment, `run_scan.py:3078`). An SNMP answer
from an already-fingerprinted host is lost and the device's SNMP column renders `—`.

When fixed, update docs/report-interpretation.md §10.3 SNMP-version table, `—` (em-dash) row.

## Feasibility & Effort

- **Verdict: CONFIRMED, effort M.** `run_scan.py:2994` (sweep), `:3026` (Unknown-only gate), `:3078` (persistence gap comment).
- Fix: record `snmp_version`/sysDescr on identified devices too, and persist via the session that owns the rows.
- Unknown: whether SNMP data should ever override a banner-derived vendor.
