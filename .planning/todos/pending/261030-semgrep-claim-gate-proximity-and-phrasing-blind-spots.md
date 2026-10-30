# The Semgrep-claim guard accepts any nearby "known defect" and misses claims worded differently

**Filed:** 2026-10-30 (Phase 235 post-GO code review, group (c): WR-06)
**Priority:** P3. A test weakness, not a shipped defect; matters because the guard is what keeps the "source scanning works" claim out of the docs.
**Source:** `.planning/phases/235-release-launch-gate/235-REVIEW.md` WR-06
**Where it lives:** **[tests only]** `tests/test_no_semgrep_working_claim.py:35-36, 64-66`.

## Defects (all verified by the reviewer with `flagged_unmarked`)

- The marker can be about an unrelated defect: README's "Known defects, scores" and "Known defects, Windows sensor"
  lines are accepted as markers for a Semgrep claim within +/-3 lines.
- The flag needs `semgrep` plus `source|cryptograph`; "Semgrep finds weak crypto in your repositories." is not
  flagged.
- The `key vault` exclusion rejects legitimate combined disclosures (false failure, not false pass).
- Only tracked `*.md` is scanned; dashboard copy, CLI help and report templates are out of scope, unstated.

Note: the new README line added 2026-10-30 ("Known defects, Semgrep not installed.") sits next to the Semgrep
ruleset line; it passed the guard, which is itself an example of the proximity looseness.

## Candidate fix

Subject-bind the marker, e.g. `(semgrep|source|ruleset).{0,80}(known defect|unavailable)|(known defect|unavailable).{0,80}(semgrep|source|ruleset)`
(case-insensitive); widen the flag to `semgrep` plus `crypto|repo|source|scan`; drop the `key vault` carve-out once
the marker is subject-bound; state the scan-set limits in the docstring (or extend to templates/help text).

## Feasibility & Effort

- **Feasibility: CONFIRMED; fix LIKELY.** Regex tightening plus fixtures for each probe above.
- **Effort: S.**
- **Unknowns:** whether the tightened flag trips existing honest docs (run it over the tree first); whether
  extending to non-`.md` surfaces is worth the false-positive cost.
- **Spike needed?** No.
