# `readme_audit.py links` and `score_attribution.py` pass vacuously

**Filed:** 2026-10-30 (Phase 235 post-GO code review, group (b): WR-04, WR-05)
**Priority:** P2. Both are release-gate evidence scripts whose green does not mean what it says.
**Source:** `.planning/phases/235-release-launch-gate/235-REVIEW.md` WR-04, WR-05
**Where it lives:** **[tooling only]**, not in the published package: `scripts/score_attribution.py`, `scripts/readme_audit.py`.

## Items

- **WR-04** `score_attribution.py:114-191, 203`: attributes *membership*, not *magnitude*. Reproduced in the review:
  `evaluate(84, 84, None, ...)` returns `ok=True` (missing dashboard score), and `evaluate(84, 84, 3, ...)` also
  `ok=True` (an 81-point gap "attributed" by one legacy-TLS severity difference). `UNBRIDGED_DASHBOARD_TITLES`
  contains `"Quantum-"`, matching nearly every non-RSA quantum-vulnerable cert finding, so almost any real scan has
  an attributable difference and SCORE-PARITY cannot detect a dashboard scoring regression.
  Fix: hard-fail on `_num(dash_score) is None`; bound the gap (recompute with attributed items removed, or a
  per-item ceiling from the scoring weights); at minimum cap and print the gap.
- **WR-05** `readme_audit.py:254-261, 298-305`: `check_links([])` returns verdict green, exit 0, with 0 links
  checked; in `pypi` mode a missing `info.description` falls back to `""`. Fix: zero checked links -> `unknown`
  (exit 2); optional `--min-links N` floor.

## Feasibility & Effort

- **Feasibility: CONFIRMED (both reproduced by the reviewer); fix LIKELY.** WR-05 is trivial. WR-04's bound needs a
  design choice, and the right ceiling depends on scoring v4 weights.
- **Effort: S** for WR-05 and the missing-score fail; **M** for a principled magnitude bound in WR-04.
- **Unknowns:** how many of the existing score-parity PASS results in Phase 235 evidence would flip under a real
  bound. That is worth knowing before 235-18 cites SCORE-PARITY as evidence.
- **Spike needed?** Small: rerun `score_attribution` over the saved evidence with a gap cap and see which flip.
