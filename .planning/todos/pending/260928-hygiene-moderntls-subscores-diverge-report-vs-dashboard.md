# Hygiene and Modern TLS subscores still diverge between report and dashboard pipelines

**Found:** 2026-09-28, Phase 210 plan 06 (live multihost re-run, Success Criterion 5 evidence)

**Severity:** Medium — residual, much smaller than the bug XSURF-01/02/03 fixed, but Success
Criterion 5 explicitly demands the two pipelines report the "identical number" and they do not, on
this live run.

## What was found

A fresh, single `docker exec chaoslab-mh-prober-1 quirk --config /scan-config.yaml
--allow-internal-targets --allow-cleartext-broker-probe` run against the freshly-rebuilt
`multihost` profile (`scan_run_id = 2026-09-28T01:41:30.088508+00:00`) was read from BOTH
pipelines:

| Metric | Report pipeline (`quirk-output/scorecard-20260928-014244.md`) | Dashboard pipeline (`GET /api/scan/latest?scan_id=...`) |
|---|---|---|
| Headline score | **17/100** | **18/100** |
| CRITICAL count | 6 | 6 (MATCH) |
| Certificate count | 20 (`intelligence-20260928-014244.json` `evidence_summary.certificate_observations.certs_observed`) | 20 (`certificates` array length) (MATCH) |
| Cap reason | "6 open CRITICAL findings — score limited to 17 (computed 69)" | "6 open CRITICAL findings — score limited to 18 (computed 74)" |

CRITICAL count and certificate count now match exactly — the XSURF-01/02/03 fixes (SAML dual-`use`
dedupe, evidence.py dedupe, `scan_run_id`-exact latest-scan resolution) are working correctly on a
live run. But the headline score still differs by 1 point, traceable to the score decomposition:

| Category | Report (scorecard) | Dashboard (`score.subscores`) |
|---|---|---|
| Hygiene | 17/25 | 21/25 |
| Modern TLS | 17/25 | 21/25 |
| Identity | 9/25 | 9/25 (MATCH) |
| Agility | 25/25 | 25/25 (MATCH) |
| Data at Rest | 22/25 | 22/25 (MATCH) |
| Data in Motion | 13/25 | 13/25 (MATCH) |

Rollup: report `103 ÷ 1.5 = 69` (capped 17); dashboard `111 ÷ 1.5 = 74` (capped 18). The 8-point gap
in the pre-cap sum is isolated ENTIRELY to Hygiene and Modern TLS (4 points each) — the other four
categories are byte-identical between pipelines. This is a narrower, different-shaped divergence
than the one XSURF-01/02/03 closed (which was a straight double-count of one certificate); it was
not visible before those fixes landed because the CRITICAL-count-driven cap was masking smaller
differences under a much larger 4-point gap.

## Suspected mechanism (not verified — no code was read for this beyond the artifacts above)

CONTEXT.md (Phase 210) explicitly scopes the ratio-denominator rewrite to Phase 211 (`DENOM-*`) and
this phase to "only stop double-counting into the existing denominators" — Hygiene and Modern TLS
are exactly the two categories most likely to be affected by denominator population differences
(e.g., which endpoints count as "assessed" for TLS hygiene) rather than by a dedupe bug. This may
already be within Phase 211's planned remit rather than a new defect — re-check against Phase 211's
CONTEXT/PLAN before scoping new work.

## Recommended next step

At Phase 211 planning (`DENOM-*`, ratio-denominator rewrite) or Phase 212 (healthy-endpoint dilution
decision), re-run this same live comparison and confirm whether the denominator fix closes this
specific 17-vs-18 gap. If it does not, this needs its own investigation before Phase 214 (release
cut) — CLAUDE.md and ROADMAP Success Criterion 5 both require the two pipelines to report the same
number, and this todo tracks the last known gap between "reported" and "true."

## Evidence trail

- `quirk-output/scorecard-20260928-014244.md`
- `quirk-output/intelligence-20260928-014244.json` (`evidence_summary`)
- `quirk-output/findings-20260928-014244.json`
- `/tmp/dash-210-06.json` (GET /api/scan/latest response, not committed — scratch capture)
- Full detail: `.planning/phases/210-cross-surface-score-parity/210-06-SUMMARY.md`
