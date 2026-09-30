# `text-primary` nav link fails AA in light theme (root/dashboard-home)

**Filed:** 2026-09-30, from Phase 218 plan 218-05 (CI-only axe baseline round-trip, D-09 residual
triage).
**Priority:** P3 — axe-confirmed live violation (~3.5:1 light, corroborating hand calculation
against white; below the 4.5:1 AA-normal-text floor).
**Owner:** Phase 220 (CI Instrument Truth).
**Status:** open, not triaged.

## What happens

`/` (root/dashboard-home), light theme: `<a class="text-primary underline" href="/trends"
data-discover="true">View trends →</a>`. `--primary` (light theme) is `180 45% 41%` (`#399797`);
against a white page background it measures ~3.5:1, below AA-normal-text's 4.5:1. Underline text
links are not automatically exempt from the color-contrast SC (1.4.1's non-color-alone exemption
covers the underline distinguishing it from body text, not the ratio itself). Axe-confirmed as a
live violation in the 218-05 CI round-trip (run 36776265139); this entry was first revealed (not
created) by Phase 216's light-theme sweep and has survived every round-trip since.

## Why it is not a Phase 218 fix

Not one of FIX-04's 3 named design-call tokens; RATCHET-01's badge baseline is `{}` as of 218-04,
and this is a text link, not a badge pair, so it is not a FIX-05 failure under REQUIREMENTS.md's
literal definition. `--primary` is also a broad, app-wide accent token (buttons, active nav state,
focus rings) — darkening it is a design call with wide blast radius, not a mechanical fix.

## Suggested first step

Either introduce a link-specific darker `--primary`-derived colour for light-theme body text links
(parallel to the `-foreground` token pattern used elsewhere), or confirm with an operator whether
`--primary` itself should darken in light theme (checking the button/focus-ring/active-nav
collateral first, the same way 218-CANDIDATES.md's collateral tables did for `--quantum-safe`).
