# Two Phase 217 visual legs could not be exercised — the canonical DB has no 30-89-day certificate and no `chart-tls` badge row

**Filed:** 2026-09-29, from the Phase 217 operator visual checkpoint (217-05; `UAT-217-07`, `UAT-217-08` recorded GAP).
**Priority:** P3 — covered at unit level (D-09 guard, badge ratchet), but never seen rendered.
**Owner:** 999.118 (HORIZON.md ledger row; backlog .planning/backlog/999.118-a11y-design-calls-and-instrument-blind-spots/).
**Re-pointed:** 2026-10-01 by Phase 221 (INT-01). The previous owner phase closed without picking this up.

## Gaps

1. `/certificates` — no certificate expiring in 30-89 days, so the protected amber text-on-white use
   (`certificates.tsx`, `daysToExpiry < 90` branch, bare `--status-warning`) never renders.
2. `/findings`, `/trends` — no row renders a `--chart-tls` badge, so the new light-theme white text
   on `--chart-tls` (6.24:1) was never observed in a browser.

## Harness lesson recorded with it

Computed-colour probes must wait for `transition-colors` (~150 ms) to settle after a theme toggle;
an immediate read returns the pre-toggle colour and looks like "the light theme isn't applying".
