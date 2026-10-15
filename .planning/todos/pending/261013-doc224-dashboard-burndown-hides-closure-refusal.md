---
type: todo
created: 2026-10-13
source: Phase 224 doc-claim ledger (DOC-04), gap closure gc2-OPS; ledger row DCL-OPS-B-0436 (docs/operators-guide.md "burndown block is empty / says not computed" troubleshooting)
priority: medium
area: quirk/dashboard/api/routes/scan.py (_derive_closure_burndown), src/dashboard/src/pages/roadmap.tsx (Remediation Burndown block)
status: pending
resolves_phase: null
owner: "999.133"
---

# Dashboard Roadmap burndown shows a table, not the refusal, on a scan whose closure was refused

When closure is refused at scan level (no comparable prior scan, missing signature, signature version gap, missing
target-set digest, or scope mismatch), the exported HTML report (and the PDF printed from it) and the DOCX report state
`Closure not computed: <reason>.`. (Correction, GC3: an earlier version of this todo also listed the CLI technical summary.
It carries no refusal and no burndown: `quirk/reports/writer.py:531` calls `build_tech_markdown` without the `burndown`
or `closure_refusal` arguments, and a `write_reports` probe with a scan-level refusal wrote the statement into HTML and DOCX
only, probe `.planning/phases/224-doc-claim-ledger-verification/work/probes/gc3-ops-cli-markdown-burndown-probe.sh`. That gap is tracked in `261013-doc224-cli-technical-report-never-renders-burndown`.)
The dashboard does not:

- `run_scan.py:4133` (`persist_remediation_snapshot`) writes the scan's remediation items and fingerprints BEFORE
  `run_scan.py:4191` (`compute_closure`) runs. A refusal returns early (`quirk/intelligence/closure.py:288-299`) and
  leaves those rows in place at their default state, `not_observed` (`quirk/intelligence/remediation.py:136`).
- `_derive_closure_burndown` (`quirk/dashboard/api/routes/scan.py:1345-1397`) only returns `unavailable_reason` when
  there are zero fingerprint rows. It never reads closure counters or refusal state, and those counters are not persisted
  anywhere (`quirk/db.py` has no closure-counter or refusal column).
- `src/dashboard/src/pages/roadmap.tsx:497-535` therefore renders the burndown table, with every item in the Not
  Verified column, and no refusal statement. No file under `quirk/dashboard/` or `src/dashboard/src/` references
  `Closure not computed` or any `refused_*` key.

The first scan of every estate hits this (`refused_no_prior`). The operators-guide now says the dashboard does not show
the refusal and points operators at the exported report. That is a documentation workaround for a product defect: the
dashboard presents "not checked" as a populated table, which is the misreading CLOSE-01 / SURF-02 exist to prevent.

- [ ] Persist the scan-level refusal (e.g. the `reason_key` from `compute_closure`'s counters) at scan time, or
      recompute comparability read-only in `_derive_closure_burndown`.
- [ ] Return it in `ClosureBurndown` (`quirk/dashboard/api/schemas.py:579`) and render the same
      `Closure not computed: <axis>.` statement on the Roadmap page instead of the table.
- [ ] Test: a refused scan with fingerprint rows yields the refusal statement, not buckets.
- [ ] Revert the operators-guide caveat (the "dashboard Roadmap page does not read the refusal" sentence) once fixed.

## Feasibility & Effort

- **CONFIRMED** the defect path by reading `run_scan.py:4127-4141` (persist) and `:4183-4204` (closure, later),
  `quirk/intelligence/closure.py:285-299` (early refusal return, rows untouched),
  `quirk/dashboard/api/routes/scan.py:1365-1374` (only a zero-row check) and `roadmap.tsx:497`.
- **LIKELY** effort **M**. Persisting the refusal needs a column or small table plus a migration (`quirk/db.py`);
  a read-time recompute avoids schema change but `select_prior_scan_run_id` (`closure.py:145-159`) picks the most
  recent OTHER scan, not the scan before this one, so it gives the wrong answer for an older scan viewed later.
- **UNKNOWN**: whether historical scans (no persisted refusal) should show "not computed" or the table. Decide before
  building. No spike needed beyond that decision.
