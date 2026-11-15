---
type: todo
status: resolved
resolves_phase: "185"
resolved: 2026-09-06
created: 2026-08-27
source: phase-165 code review (CR-01) + 165-VERIFICATION.md
priority: medium
---

# a11y sweep does not cover /hardware or /compare

`src/dashboard/tests/a11y/routes.json` sweeps 11 routes. It omits `/hardware`
and `/compare`.

**Why it matters:** this gap is precisely why Phase 165's CR-01 escaped detection.
`--ds-text-muted` shadowed D-10's `--muted-foreground` contrast fix, so
`.label-eyebrow` shipped `#6e7a95` (4.46:1 — below AA for 10px normal-size text).
Its only consumers — `LifecycleEventRow.tsx`, `VendorTrendRow.tsx` — render
exclusively on `/hardware` and `/compare`, so the axe sweep never loaded them.
The bug was caught by code review, not by the gate that exists to catch it.

CR-01 itself is fixed (commit `2ccc7ea`) and guarded by a targeted unit test
(`src/dashboard/src/components/__tests__/muted-token-contrast-guard.test.ts`),
but that guard is token-specific. The general blind spot remains: any
accessibility regression confined to those two routes is currently invisible.

**Work:**
1. Add `/hardware` and `/compare` entries to `tests/a11y/routes.json`.
2. Generate `baseline-hardware-*.json` and `baseline-compare-*.json` for all
   three variants (default/empty/loading) via `npm run a11y:baseline`,
   `:empty`, `:loading`.
3. Triage whatever the sweep surfaces. Note Phase 156's HWLC-11 advisory-only
   firewall deliberately hardcodes `hsl()` literals on these routes — expect
   findings there, and decide per D-11 whether each is token-fixable (fix) or a
   scoped design decision (justify in the ledger).
4. Confirm `npm run a11y:check` still exits 0 across all variants afterward.

**Watch out:** these two routes are guarded by `lifecycle-advisory-guard.test.ts`
and `vendor-trend-advisory-guard.test.ts`. Do not "fix" their raw `hsl()`
literals into design tokens — that firewall is intentional (Phase 156 D-07).

---

**Cross-reference (added 2026-09-02, Phase 177-07):** see also
`a11y-baseline-environment-mismatch.md` in this same directory — a related a11y-gate fidelity gap
found independently (macOS-generated baselines vs. Linux-enforced gate, discovered on
`Dashboard Quality`'s first-ever execution against the v5.16/v5.17 `main` history). Both gaps
concern coverage/accuracy of the same axe baseline system and should be triaged together: this
item's `/hardware`/`/compare` routes have never been swept at all, and the other item's already-
swept routes may still be carrying unverified macOS-generated baselines the same way
`data-at-rest` was until this phase.


---

## Disposition (Phase 185, 2026-09-06)

**Work item 1 (routes.json entries) — DONE.** `/hardware` and `/compare` added to
`src/dashboard/tests/a11y/routes.json` (plan 185-05), landed atomically with their baselines
(commit `3ea9e40e`).

**Work item 2 (generate baselines, all 3 variants) — DONE.** Six baselines
(`baseline-{hardware,compare}-{default,empty,loading}.json`) generated on real Linux CI
(`a11y-regenerate-baselines`, run `34067584788`, ubuntu-24.04, Chrome 152.0.7977.82) and
installed — not generated locally on macOS, closing the same environment-mismatch concern as
`a11y-baseline-environment-mismatch.md`.

**Work item 3 (triage findings) — DONE.** Both routes surfaced `color-contrast` (Phase 156
HWLC-11 raw `hsl()` badge literals, D-11 firewall — justified in the ledger, deliberately NOT
fixed, per this todo's own "do not fix" warning) and `scrollable-region-focusable` (same shared
`table.tsx` overflow wrapper gap already justified on `/data-at-rest`, deferred per 165-CONTEXT.md's
scope exclusion of focus-order fixes — same disposition as
`a11y-baseline-environment-mismatch.md`'s item 3). Full per-entry justifications are in the six
baseline JSON files and `ACCEPTED-VIOLATIONS.md`.

**Work item 4 (confirm `a11y:check` exits 0 across all variants) — DONE.** `Axe + Console Gate`
GREEN on `ubuntu-latest` at commit `3ea9e40e`, run `34068026959`, all three variants
(`a11y:check`, `:empty`, `:loading`), both new routes PASS with zero unjustified count increases.

**The advisory firewall (`lifecycle-advisory-guard.test.ts`, `vendor-trend-advisory-guard.test.ts`)
was NOT touched**, per this todo's own warning — both guard suites remain green (29/29 each).

See `185-05-SUMMARY.md`, `185-07-SUMMARY.md`, and `Phase-185-A11y-Baseline-Environment.md` (vault)
for full evidence.
