---
type: todo
created: 2026-11-04
source: "Phase 235.1 code review (235.1-REVIEW.md), items deferred by the orchestrator"
priority: low
area: scripts/release_smoke_inner.sh, scripts/score_attribution.py, quirk/cli/doctor_cmd.py, quirk/__init__.py, tests/
status: pending
owner: "999.127"
target_release: "5.29"
---
# Phase 235.1 review: deferred warnings and info items

**Filed:** 2026-11-04. The orchestrator fixed the WR-01..06, IN-01, IN-02 and IN-07 review findings before plan 14 pushed,
because they contradicted claims in the [5.28.1] CHANGELOG. The items below cannot produce a false PASS or a false clean
result, so they were deferred. The full text and proposed fixes are in
`.planning/phases/235.1-install-source-scan-truth-fixes-inserted/235.1-REVIEW.md` (untracked; this summary is the durable copy).

- **WR-07** `scripts/release_smoke_inner.sh:94-118, 264-271`. README commands containing `cd`/`source`/`export` run
  in-shell with no watchdog, so a `cd … && pip install …` line can hang the leg. On the macOS/contributor legs the
  fallback watchdog kills only the wrapper shell, and orphaned pip/scan children can pollute later checks. It does not
  produce a false PASS: the leg hangs or FAILs.
- **WR-08** `tests/test_source_error_rows_score.py`. The test pins a headline of 81 with 3 domains "assessed" for a scan
  whose only source output is a failed repo. That scoring behaviour predates 235.1, but the test now records it as
  expected. Decide whether a zero-evidence domain should count as assessed, then re-pin the test.
- **WR-02 residual** (from fix 9a3cf374). A single source target that exits 0 with only semgrep error entries still
  records the phase `ran`, with one in-band error row. That row counts as a scan error and, since cb0b993c, is surfaced in
  `partial_failures`, so the result is not clean, but the phase status still reads `ran`. Plan 03 pins this shape as
  returning a row rather than raising. Decide whether an error-only result should record `failed`.
- **IN-03** `timeout -k 5` expiry can return 137, which skips the "timed out" diagnostic. The leg still FAILs.
- **IN-04** `score_attribution.evaluate` crashes instead of printing a FAIL line when the HTML score is missing. It still
  fails closed through a non-zero exit.
- **IN-05** Host-leg copies of the wheel and divergence set are not recorded in `COPY_FAILED`.
- **IN-06** Doctor reads `./config.yaml` without `encoding=`, a Windows cp1252 risk.
- **IN-08** Two tests use a row shape that differs from the one production emits.
- **IN-09** The `quirk/__init__.py` version fallback leaves helper names in the package namespace.

## Feasibility & Effort

All are small and local: about one day in total. WR-08 needs a scoring decision first (it changes no code by itself).
WR-07's portable fix is a process-group kill (`setsid`, or `kill -- -$pgid`) on the fallback watchdog. Test it with the
existing stub-docker harness in `tests/test_release_smoke_harness.py`.
