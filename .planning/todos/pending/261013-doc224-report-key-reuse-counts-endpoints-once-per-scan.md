---
type: todo
created: 2026-10-13
source: Phase 224 GC3-R3 (part 05, docs/report-interpretation.md §21 Key Reuse)
priority: medium
area: quirk/intelligence/key_reuse.py, quirk/reports/writer.py
status: pending
resolves_phase: null
owner: "999.132"
---

# Report Key Reuse counts rows across scans: one endpoint scanned twice forms a cluster of itself

The report's Key Reuse section is cross-scan by design (D-03; `quirk/reports/writer.py` loader calls
`compute_key_reuse_clusters(session)` with no `scan_run_id`). The query counts rows, not endpoints:
`total` counts every TLS row (`quirk/intelligence/key_reuse.py:90-97`) and clusters use
`func.count(CryptoEndpoint.id)` (`:110-115`). One `host:port` scanned twice with an unchanged key becomes a "cluster"
of itself, and pre-5.21 NULL-fingerprint rows stay in `M` forever, so re-scanning never raises the ratio. Probe
`gc3-r3-f5-*`.

When fixed, update docs/report-interpretation.md §21 (coverage line, cluster reading, pre-5.21 paragraph).

## Feasibility & Effort

- **Verdict: LIKELY, effort S-M.** `key_reuse.py:90-97,110-115`; scoped variant already exists (`quirk/intelligence/exposure_map.py:89` passes `scan_run_id`).
- Operator choice: dedupe to distinct (host, port) per fingerprint (latest row), or scope the report to the run.
