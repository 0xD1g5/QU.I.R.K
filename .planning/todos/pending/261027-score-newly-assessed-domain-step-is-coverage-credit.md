---
type: todo
created: 2026-10-27
source: Phase 234 (O-6; decision record §10)
priority: medium
area: quirk/intelligence/scoring.py (Phase 188 exclude-and-rescale), tests/test_score_newly_assessed_domain.py
status: pending
resolves_phase: null
owner: "999.139"
---

# The first clean row of a not-yet-assessed domain still raises the headline score

**Owner:** 999.139

SCORE-09 (Phase 234, scoring 4.0) stopped healthy endpoints from raising the score inside domains that are
already assessed. It deliberately did not change what happens when a scan observes the **first** row of a
domain that was not assessed: Phase 188's exclude-and-rescale brings that domain in at 25/25, which raises the
headline. That is coverage credit, not dilution, but a client can still see the number improve because the scan
looked at one more protocol.

Measured on 4.0 with one clean SMTP-STARTTLS row (`.planning/decisions/234-p2b-fix-and-ladder-remeasurement.md`
§10, from `234-residuals.md` §2):

| Rung | before (domains) | after (domains) |
|------|------------------|-----------------|
| R2 | 77/92 (5) | 78/93 (6) |
| R3 | 44/82 (5) | 46/85 (6) |
| R4 | 22/66 (5) | 24/72 (6) |

The 3.0 scorer gives the same numbers, so the step predates 4.0. It is pinned as deliberate by
`tests/test_score_newly_assessed_domain.py::test_newly_assessed_domain_step_is_deliberate_coverage_credit`
(R2/R3/R4; UAT-234-07).

## Proposed fix shape

This needs an operator decision before any code:

- **Keep it** and say so in `docs/report-interpretation.md` (a newly covered domain raises the score once, by design); or
- **Enter a new domain at a neutral value** (for example the mean of the assessed domains) instead of 25/25, so
  only its weaknesses move the headline; or
- **Require a minimum population** before a domain counts as assessed.

Whichever is chosen, the pin above changes from "the step exists" to the new property, and the ladder must be
re-measured (every rung moves if the entry value changes).

## Feasibility & Effort

**CONFIRMED** by the measurement above. Effort **S-M** once decided; the decision is the unknown.
