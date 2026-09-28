# A mutator's encoded SCENARIO must be checked against the defect's own definition before measuring

**Filed:** 2026-09-28 (Phase 212, DILUTE-01 spike)
**Owner phase:** unassigned — candidate for a CLAUDE.md standing-lessons entry
**Tag-blocking:** no

## The failure this generalises

Phase 212 measured three candidate denominators for the P2b dilution defect. Two of them were
measured with mutators whose **encoded scenario was never checked against the defect's own
definition** before the first measurement was taken.

- **scan-scope normalisation** initially read as a clean `PASS` — computed score flat at 71 across
  the whole +0/+20/+100/+500 sweep. The arithmetic was correct. But holding `P2B_REQUESTED_SCOPE`
  fixed models *"we looked harder within the same request"*, whereas the defect's own opening
  sentence is *"Scanning more ports on the same hosts improves the client's grade."* Under that
  reading the requested scope grows in lockstep with the returned rows, the divisor tracks the
  numerator, and the series is `71 -> 74 -> 78 -> 82` — **identical to control, zero mitigation.**
- **distinct hosts** held an asserted `host_count` constant, which defeats dilution by construction.

## Why the existing guards did not catch it

This project's recorded anti-patterns cover: a gate that passes because it is vacuous; a
falsification that comes back PASS; a hand-maintained list drifting from the real set; measuring a
component with its own extractor. **None of them cover this one.** Every internal check passed:
the numbers were reproducible, the harness was correct, the predicate was hard and non-tolerance,
rounding-collapse was ruled out. The measurement was sound. **The thing being measured was wrong.**

It surfaced only when the SAME falsifiability test that had been applied to one candidate was
applied symmetrically to the other. The asymmetry — one row audited, one row exempt — was the tell.

## The rule

Before the first measurement of any candidate/variant:

1. **State in writing what scenario the injection encodes.**
2. **Quote the defect's own definition** and check the encoding against it, literally.
3. **Answer "what input would make this row FAIL?"** If the answer is "none", the row is a
   tautology — label it in the RESULTS TABLE CELL, never a footnote.
4. **Apply (3) to every row, not just the suspicious one.** Selective auditing is how the sound-
   looking row escapes.

## Relationship to existing rules

Extends `feedback_measure_with_a_method_independent_of_the_audited_code` — that rule says use a
different instrument. This adds: **also check you are pointing the instrument at the right thing.**
An independent instrument measuring the wrong scenario still yields a confident wrong answer.

## Evidence

- `.planning/decisions/212-score-dilution-denominator-decision.md` — the DILUTE-01 decision record.
- `.planning/phases/212-score-dilution-decision-only/212-MEASUREMENTS-denominator.md` — the
  follow-up falsifiability audit that overturned the initial PASS.
