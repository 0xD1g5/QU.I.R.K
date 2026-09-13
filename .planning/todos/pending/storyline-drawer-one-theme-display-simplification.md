---
type: todo
created: 2026-09-12
source: phase-202 plan 05 (D-08/D-09); filed at plan 202-08 close
priority: low
requirement: none (deliberate simplification recorded for future revisit, not a defect)
---

# Storyline drawer shows only ONE remediation theme per finding — a deliberate simplification, not a data-model fact

`202-CONTEXT.md`'s D-08 established that a finding can belong to more than one remediation theme at
once — verified live against `./quirk-output/quirk.db`: **28 of 67 distinct fingerprints (41%)
belong to 2+ themes.** The pattern found was uniform: every one of those 28 multi-theme cases pairs
the `high-impact-findings` severity catch-all with exactly one specific title-based theme
(`plaintext-http-exposure` ×21, `self-signed-certificates` ×5, `expired-certificates` ×2).

## The resolution this phase shipped

When a finding maps to 2+ themes, the drawer renders the specific title-based theme and never the
`high-impact-findings` catch-all (D-08's tie-break, implemented in `storyline.py`'s
`_theme_attribution_for_finding`, proven by a test that derives the expected winner from
`REMEDIATION_CONSTITUENCY` at run time rather than a hand-written slug string). When the catch-all is
a finding's ONLY theme, it renders instead of being suppressed (D-09, closing a gap D-08 left open —
suppressing it would be a fabricated absence for a finding that genuinely has a real lift).

**The drawer never discloses that a finding also belongs to a second theme.** CONTEXT.md's D-08
explicitly rejected showing both: "showing two conditioned lift numbers side by side would make the
non-additivity point substantially harder to convey, which is the whole problem D-01 exists to
solve." This is the right call for the phase's scope, but it means an operator resolving a
plaintext-HTTP finding today never learns from the drawer that the same finding also contributes to
the `high-impact-findings` catch-all's own lift — only the specific theme's number is ever shown.

## Why this is worth revisiting, not why it is wrong today

The one-rule resolution works because **all 28 observed overlaps pair a specific theme with the
same severity catch-all.** If a future finding class or remediation-theme definition ever produces
an overlap that is NOT the severity catch-all — two specific, non-severity themes both claiming the
same finding — the current tie-break has no defined behavior for that case (202-05's SUMMARY notes a
residual 2+-specific-slug branch exists in code, picked deterministically via `sorted(...)[0]` with
a warning log, but this is explicitly "not observed in live data," not a designed behavior).

**Do not build a hand-ordered priority list to solve this if it happens.** `202-CONTEXT.md`
explicitly rejected a hand-maintained `_SLUG_PRIORITY` list for this exact reason — a hand-maintained
list of sites is this repo's documented recurring failure mode (CLAUDE.md's `state.*` verb-integrity
section records four instances in the GSD toolchain alone). The correct trigger to revisit this todo
is a test that derives the overlap set from data and finds a non-catch-all overlap, not a developer
noticing one by inspection.

## Acceptance (for whoever picks this up)

- A monitoring test (or a periodic data check) that flags the first non-catch-all multi-theme
  overlap the moment it appears in real scan data, rather than relying on someone noticing.
- A design decision — informed by that first real overlap case, not invented in the abstract — for
  whether the drawer should ever disclose a second theme, and if so, how without undermining D-01's
  non-additivity messaging.
- Cite `202-05-SUMMARY.md`'s tie-break implementation and the 28/67 live figure as the baseline this
  todo's eventual fix should compare against.
