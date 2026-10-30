---
type: todo
created: 2026-10-12
source: Phase 224 doc-claim ledger (DOC-04, D-10); ledger rows DCL-REPORTINT-0014 and DCL-REPORTINT-0153 (docs/report-interpretation.md sections 3.4 and 17)
priority: low
area: quirk/intelligence/scoring.py, tests/test_score_weights_invariant.py, quirk/intelligence/evidence.py
status: pending
resolves_phase: null
owner: "999.131"
---

# Three code comments repeat figures the code no longer has

Found while checking `docs/report-interpretation.md` figures against the code. Comments only, no behaviour:

- `quirk/intelligence/scoring.py:66-67` says the `SCORE_WEIGHTS` sum "is 275.0 BY DESIGN (Phase 83 rebalance)". The live
  sum is 297.0 (`.venv/bin/python -c "from quirk.intelligence.scoring import SCORE_WEIGHTS as w; print(sum(w.values()))"`),
  and `tests/test_score_weights_invariant.py:54` asserts 297.0.
- `tests/test_score_weights_invariant.py:6` (docstring) says "must be 303.0 by design" while its own assertion at line 54
  checks 297.0 (the `agility_high_impact_ratio` weight was removed by the v3 scoring change).
- `quirk/intelligence/evidence.py:37` says CLOSED rows are filtered "by quirk/reports/technical.py:88"; the filter is at
  `quirk/reports/technical.py:155`. `docs/report-interpretation.md` section 17 had copied the stale line number.

- [ ] Update the three comments, keeping `tests/test_score_weights_invariant.py` as the single source for the expected sum.

## Feasibility & Effort

**CONFIRMED** (each figure re-derived by running the code or reading the cited line). Effort **S**. Unknowns: none.
**Spike**: not needed. Note `tests/test_score_weights_invariant.py` must keep passing; no weight value changes.
