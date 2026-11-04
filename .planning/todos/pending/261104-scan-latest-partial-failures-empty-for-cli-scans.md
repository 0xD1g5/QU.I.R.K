---
type: todo
created: 2026-11-04
source: "Phase 235.1 plan 01 SUMMARY deviation 2; plan 04 checkpoint data-source note"
priority: medium
area: quirk/dashboard/api/routes (GET /api/scan/latest)
status: pending
owner: "999.127"
target_release: "5.29"
---
# `/api/scan/latest` returns empty `partial_failures` for a CLI-only scan

**Filed:** 2026-11-04 (Phase 235.1 execution). Explicitly kept OUT of 235.1 scope, per the operator.

## The defect

`GET /api/scan/latest` resolves the scan checkpoint key only through a completed `ScanJob` row created in the
last 30 minutes. A scan started from the CLI (`run_scan.py` / `quirk scan`) creates no `ScanJob`. So `partial_failures`
comes back empty even when the checkpoint row exists in the DB (confirmed by a direct query in 235.1-01).

## Consequence

The Executive page's `ScannerStatusCard` reads `PartialFailureEntry.error_category` from that route. After 235.1, a
configured-but-missing semgrep/syft produces a `missing_binary` skip. On a CLI-only scan the Executive card's
"Skipped" badge never appears, even though the Scan Coverage chip (which reads scan-phase records) shows it.
That is a dashboard-first product (see memory `project_gui_first_positioning`) under-reporting the one CR-02 case
235.1 exists to surface.

## Candidate fix

Resolve the checkpoint key from the latest scan run directly, the way the coverage API reads scan-phase records,
and fall back to the `ScanJob` lookup only for in-flight dashboard jobs. Add a regression test that runs a bare
CLI scan with semgrep absent and asserts that `partial_failures` carries the `missing_binary` entry.

## Feasibility & Effort

Small: one route plus one test, about half a day. Risk: other consumers of `partial_failures` that rely on the
30-minute window. Grep the dashboard for `partial_failures` before changing it.
