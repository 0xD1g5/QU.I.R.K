---
type: todo
created: 2026-11-16
source: Phase 236 review WR-04 and WR-05 (236-REVIEW.md), filed by plan 236-09
priority: low
area: tests/test_severity_divergence_behaviour.py
status: pending
resolves_phase:
owner: "999.132"
---

# The divergence gate keys on severity not title, and one disposition absorbs every residual at its key

WR-04: `_disposition_key` matches any title at a residual's `(host, port, severity)` key and returns the first ledger match, so one
disposition can absorb several residuals in a family. WR-05: the diff keys on severity, not canonical title, which departs from
D-07's wording; a same-severity substitution on one host:port is invisible to the gate.

Fix: match each residual's own title and assert expected residual counts per entry; add a title-aware second pass for bridged titles.

## Feasibility & Effort

**Feasibility: HIGH.** Test-only. **Effort: M.** Needs care so the three existing dispositions keep matching.
