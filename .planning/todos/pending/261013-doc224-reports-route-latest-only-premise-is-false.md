---
type: todo
created: 2026-10-13
source: Phase 224 GC2 re-audit (R05), ledger part 224-05, docs/report-interpretation.md §26 "Only the latest scan is reachable, and why"
priority: low
area: quirk/dashboard/api/routes/reports.py (module docstring D-02/D-06), docs/operators-guide.md (report endpoints)
status: pending
resolves_phase: null
---

# The "nothing on disk associates scan_run_id with the report stamp" premise is false

`quirk/dashboard/api/routes/reports.py:12-20` (D-06) and, until GC2, `docs/report-interpretation.md` §26 said the
report downloads are latest-only because "the report stamp is render time, not `scan_run_id`, and nothing on disk
associates them". The doc called this "a real, permanent constraint". The association does exist on disk:

- `run_scan.py:2059` `scan_run_id: Optional[str] = run_stats["started_utc"]` (the scan id is the run's `started_utc`)
- `run_scan.py:552` `ep.scan_run_id = scan_run_id` (that value is stamped on the run's endpoint rows)
- `quirk/reports/writer.py:952` `stats_path = os.path.join(outdir, f"run-stats-{stamp}.json")` writes `run_stats`,
  including `started_utc`, under the same `{stamp}` as `report-{stamp}.*`
- Probe (isolated HOME): `write_reports(..., run_stats={"started_utc": "2026-10-13T10:00:00+00:00"})` wrote
  `run-stats-20261013-114341.json` containing that `started_utc` next to `report-20261013-114341.html`.

So the `run-stats-{stamp}.json` file is a join key from stamp to `scan_run_id`. Latest-only downloads are a scope
choice, not a structural impossibility. Per-scan downloads would still need a new, validated path parameter (the D-04
containment decision the docstring names), but the "no association exists" reason is wrong. The doc was narrowed in
GC2. The module docstring still needs correcting (operators-guide.md does not repeat the premise). Product
behaviour is unchanged and is not a defect.

## Feasibility & Effort

- Correct the docstring wording: CONFIRMED, S. The claim is checked at the file:line references
  above. It is a comment and doc edit with no behaviour change.
- Per-scan report download (optional follow-up): LIKELY, M. `_select_stamp` (`reports.py:155-194`) already reads
  run-stats files, so an index from `started_utc` to `{stamp}` can be built by globbing `run-stats-*.json`. Unknowns:
  scans run without `run_stats` (`writer.py:951-953` only writes run-stats when it is provided), resumed scans
  (`run_scan.py:2078` rewrites `started_utc` to the original id, so two stamp groups can share one `scan_run_id`), and
  the D-04 path-containment review. Spike recommended before building it, not before the wording fix.
