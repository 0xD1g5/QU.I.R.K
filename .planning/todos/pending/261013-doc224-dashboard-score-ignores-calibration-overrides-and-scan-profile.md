---
type: todo
created: 2026-10-13
source: Phase 224 doc-claim ledger (DOC-04), gap closure gc2-OPS (fork A2); ledger rows DCL-OPS-A-0559, DCL-OPS-A-0570..0573 (docs/operators-guide.md "Score parity across the two pipelines")
priority: medium
area: quirk/dashboard/api/routes/scan.py (get_latest_scan scoring block, _derive_roadmap)
status: pending
resolves_phase: null
---

# Dashboard score ignores `intelligence.calibration_overrides` and uses the newest run's profile for every scan

The operators-guide used to say that `"HTTP on TLS-designated port"` is "the one known way" the report and the
dashboard can still diverge on the headline score / subscores. Two more code-evident ways exist:

1. **Calibration overrides.** The report scores with
   `compute_readiness_score(evidence, profile=cfg.intelligence.profile, weights=cfg.intelligence.calibration_overrides or None)`
   (`quirk/reports/writer.py:545-549`). The dashboard calls
   `compute_readiness_score(evidence, profile=stored_profile)` with no weights (`quirk/dashboard/api/routes/scan.py:1854`);
   `_derive_roadmap` has no weights parameter either. `tests/test_score_lift_cross_surface_numbers.py:4-19` already
   records this "pre-existing asymmetry ... RESEARCH Pitfall 4" as out of scope, but nothing tracks fixing it.
2. **Profile of the wrong scan.** `stored_profile` comes from `_latest_intelligence(_output_dir)`
   (`scan.py:1838-1846`; `quirk/validate.py:43-47` picks the newest intelligence file by mtime), even when
   `GET /api/scan/latest?scan_id=<older scan>` is requested. An older scan run with a different `--score-profile`
   is rescored with the newest run's profile.

`tests/test_cross_surface_parity.py::test_xsurf04_three_number_cross_surface_equality` scores surface A with
`profile=None` and no weights, so it cannot catch either.

The doc now lists all three causes. Fix options:

- [ ] Persist the scan's calibration (profile + overrides) per `scan_run_id` (or read the intelligence file matching
      the requested scan) and pass both to `compute_readiness_score` and `_derive_roadmap` on the dashboard.
- [ ] Extend the XSURF-04 parity test with a non-default profile and a non-empty override.
- [ ] Then narrow the operators-guide paragraph back.

## Feasibility & Effort

- **CONFIRMED** by reading `quirk/reports/writer.py:545-549`, `quirk/dashboard/api/routes/scan.py:1836-1854`,
  `quirk/validate.py:43-47` and the test docstring above.
- **LIKELY** effort **M**: intelligence files are named by stamp, not `scan_run_id`, so mapping a requested scan to its
  calibration needs either a stored column or a stamp lookup (same association gap as the report-artifact routes).
- **UNKNOWN**: whether older scans should keep their own profile or be rescored under the current one (a product
  decision). No spike needed beyond that decision.
