---
resolves_phase: null  # was 215 (closed); owner is 999.118
---

# UAT-7-21: two Pass Criteria bullets are covered by no instrument

**Filed:** 2026-09-28 (Phase 213 close, UIFIX-02)
**Owner:** 999.118 (HORIZON.md ledger row).
**Re-pointed:** 2026-10-02 by the v5.26 re-audit. Its `resolves_phase: 215` named a closed phase and 217 declined it ("not badges"); a rendered-value colour instrument is a 999.118 blind spot.
**Tag-blocking:** no — but read the caveat below before a release cut

## What

`UAT-7-21` ("Dashboard Theme — No Hardcoded Colors") is now dispositioned **PASS (qualified)**.
Two of its Pass Criteria bullets are **covered by no automated instrument and by no recorded
manual check**:

1. the **electric-blue accent value**
2. **dark-background consistency**

They are named explicitly in the disposition rather than absorbed into the PASS — that is
deliberate, and this todo exists so the naming does not become the whole of the follow-through.

## Why it is not a defect, and why it still matters

`hardcoded-color-audit.test.tsx` is a **SOURCE** test. It asserts that no hardcoded colour literal
appears in the audited files. It is structurally incapable of asserting anything about a
**rendered** value: it would pass identically if a token resolved to the wrong colour, or to no
colour at all. Phase 213's operator walkthrough (plan 213-09) covered the three Cytoscape graphs,
the certificates sort and a two-PDF light/dark comparison — it did **not** enumerate these two
bullets.

So the position is honest but incomplete: the *mechanism* is verified, two *appearance* claims are
not.

## Caveat for Phase 214 (Release Cut)

Not tag-blocking on its own. But a release tag freezes the shipped appearance, and `UAT-7-21` will
read **PASS** in the corpus at tag time. A reader who does not open the disposition text will not
know these two bullets were never checked. If the tag is meant to carry a fully-verified UAT-7-21,
close this first.

## Suggested fix

Either:
- a rendered-value assertion for the accent token and a dark-background contrast check (note the
  jsdom limitation 213-06 hit: jsdom returns unresolved `var(--token)` strings rather than computed
  colours for stylesheet-sourced rules, so this likely needs a real browser context, e.g. the
  existing Playwright path); or
- an explicit manual check added to the UAT walkthrough, so the coverage is recorded rather than
  assumed.

## Evidence

- `docs/UAT-SERIES.md` — `UAT-7-21`'s disposition names both bullets.
- `.planning/phases/213-shipped-product-defects/213-VERIFICATION.md` — status `passed`, and
  confirms the bullets are uncovered rather than treating the PASS as complete.
- `.planning/phases/213-shipped-product-defects/213-09-SUMMARY.md` — what the operator DID check.
