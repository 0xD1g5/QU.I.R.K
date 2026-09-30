# The HWLC-11/HWLC-19 advisory-firewall hues (TEAL + magenta) fail AA text contrast in light theme

**Filed:** 2026-09-30, from Phase 218 plan 218-05 (CI-only axe baseline round-trip, D-09 residual
triage).
**Priority:** P2 — a confirmed, axe-measured contrast failure (not just an instrument-coverage
gap), on a design-decision literal that a dedicated guard already protects for a different reason.
**Owner:** Phase 220 (CI Instrument Truth).
**Status:** open, not triaged.

## What happens

`lifecycle-advisory-guard.test.ts` (Phase 156 HWLC-10/11) and `vendor-trend-advisory-guard.test.ts`
(Phase 161 HWLC-19) pin a small `FORBIDDEN_PALETTE` of hues — `hsl(180 37% 47%)` (TEAL,
`#4ca4a4`) and `hsl(300 45% 55%)` (magenta) among them — to keep the lifecycle/vendor-trend
advisory sections visually distinct from the app's scored-finding palette. Both guards assert the
literal stays OUT of a forbidden set; neither asserts the literal itself clears AA text contrast
against the surfaces it renders on. It does not: TEAL vs a white/light card background measures
~2.9:1 (below the 4.5:1 AA-normal-text floor); the magenta measures ~3.9:1 (2026-09-30 hand
calculation, corroborating only — re-derive with the project's own `color-contrast-helpers.ts` at
fix time).

Confirmed live in the 218-05 CI axe round-trip (run 36776265139, artifact
`a11y-baselines-36776265139`), via a temporary local per-node probe in `run-a11y.mjs` (reverted
before commit, per 218-05-PLAN.md's sanctioned diagnostic):

- `/compare`, light theme: `label-eyebrow` span ("Recent Lifecycle Changes",
  `LifecycleEventList.tsx:58`, TEAL) + `LifecycleEventRow.tsx`'s "Worsened" direction-indicator
  span (`LifecycleEventRow.tsx:47`, magenta).
- `/hardware`, light theme: the same two `LifecycleEventList.tsx:58` (TEAL, "Recent Lifecycle
  Changes") and `LifecycleEventRow.tsx:47` (magenta, "Worsened") nodes, plus a third:
  `VendorTrendList.tsx:45` (TEAL, "Vendor PQC Status Trends").

## Why it is not a Phase 218 fix

FIX-04 named exactly 3 design-call tokens (`--destructive`, `--quantum-safe`, `--badge-modbus`);
none of these hues are one of them. FIX-05 is defined by REQUIREMENTS.md as "zero badge pair
anywhere in the dashboard below 4.5:1... verified by RATCHET-01 reporting an empty baseline" —
`badge-contrast-baseline.json` is `{}` as of 218-04, and these are non-badge text/eyebrow nodes,
not RATCHET-01 badge pairs. Changing the firewall hue is a design call (it exists specifically to
look different from the scored palette) and needs the same operator visual-review process FIX-04
used, not an auto-pick.

## Suggested first step

Bring a lighter/darker variant of each forbidden hue to an operator checkpoint (same shape as
218-03's FIX-04 review), then add a contrast assertion to `lifecycle-advisory-guard.test.ts` /
`vendor-trend-advisory-guard.test.ts` alongside the existing forbidden-palette assertion so a
future hue change cannot silently reintroduce this gap.
