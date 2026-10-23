---
type: todo
created: 2026-10-23
source: Phase 230 orchestrator, xsurf07 date-bomb investigation (debugger sweep, 2026-10-23)
priority: high
area: tests/browser_e2e_harness.py (:47, :256), tests/test_cross_surface_parity.py, tests/test_evidence_finding_vocabulary_parity.py:79, tests/test_finding_engine_parity.py:38/:46/:69, tests/test_dashboard_scoring_findings.py:27/:116
status: pending
resolves_phase: null
owner: "999.134"
due: 2026-11-10
---

# The browser E2E harness's seeded certificate expires on 2026-11-10, and other fixtures mix fixed and wall-clock dates

Found 2026-10-23 while root-causing
`tests/test_cross_surface_parity.py::test_xsurf07_compare_includes_identity_findings`. That test's pinned score
moved 31 -> 32 at 2026-10-17 09:15 UTC because its fixture fixed `scanned_at` while one certificate was wall-clock
relative. It was fixed in commit `d5b66337` by putting the fixture on one clock. A frozen-clock sweep of 121 score and
finding test files (FREEZE_AT 2026-10-01 .. 2028-03-01) found no other test that fails today. It did find these latent
cases of the same class:

- **Time-sensitive: `tests/browser_e2e_harness.py:47`, `:256`.** The seeded certificate expires at **2026-11-10
  12:00**, 45 days after the 2026-09-26 scan date. The finding generators measure expiry against the wall clock, so
  from that moment the seeded dashboard gains an "expired" CRITICAL and its scores are capped. It has shown a MEDIUM
  "expiring within 30 days" since 2026-10-11. `test_browser_e2e.py` deliberately asserts no scores or counts, but any
  visual or a11y baseline captured from that seeded page will change. **This was not checked.** Check the Dashboard
  Quality baselines (Axe + Console Gate, E2E Smoke) before 2026-11-10, because Phase 235's launch gate runs after that.
- **Mixed-clock fixtures with no pinned score today:** `tests/test_finding_engine_parity.py:38` + `:69` (fixed
  2026-08-25 `scanned_at`, now+10d cert; already past its crossing) and `tests/test_dashboard_scoring_findings.py:27` +
  `:116` (fixed 2026-10-15, now+10d; evidence crossing 2026-11-04 12:00 UTC; compares only HIGH/CRITICAL, so it is
  currently unaffected).
- **Far off, same class:** 2030-01-01 certificates in the XSURF-04 fixture (`tests/test_cross_surface_parity.py`),
  `tests/test_evidence_finding_vocabulary_parity.py:79` (pins `_EXPECTED_MODERN_TLS_SUBSCORE = 18`) and
  `tests/test_finding_engine_parity.py:46`. They gain a MEDIUM from 2029-12-02 and a CRITICAL from 2030-01-01.

- [ ] Make `tests/browser_e2e_harness.py`'s seeded certificate date relative to the wall clock, or far-future, and
      re-check any baseline captured from it. Do this before 2026-11-10.
- [ ] Put the mixed-clock fixtures above on one clock: `scanned_at` = wall clock, as in `d5b66337`.
- [ ] Optional guard: a test that fails when a fixture combines a fixed `scanned_at` with a `datetime.now()`-relative
      `cert_not_after`.

The product-side root cause is evidence measuring against `scanned_at` while the finding generators measure against
the wall clock. That stays with `261015-xsurf-history-rescored-against-wall-clock-cert-expiry` (same owner).

## Feasibility & Effort

- **CONFIRMED.** Debugger sweep 2026-10-23, with a frozen-clock plugin that reproduced the original failure. Lines are
  cited above.
- **Effort: S.** Fixture date edits plus a baseline re-check. The baseline check is the only unknown.
- **Spike: no.**
