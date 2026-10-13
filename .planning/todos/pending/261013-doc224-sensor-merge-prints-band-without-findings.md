---
type: todo
created: 2026-10-13
source: Phase 224 doc-claim ledger (DOC-04), gap closure GC3-OPS fork G; ledger rows DCL-OPS-GC3G-0003/0004 (docs/operators-guide.md §17 Troubleshooting); extended in A3FIX (evidence audit 3) with the Slack drift-notification band
priority: medium
area: quirk/cli/sensor_cmd.py (merge output), quirk/merge/scan.py (findings-less scoring), quirk/notify/payload.py + quirk/notify/channels/slack.py (drift band), quirk/intelligence/trends.py (false comment)
status: pending
resolves_phase: null
---

# `quirk sensor merge` and the Slack drift notification show a readiness band computed without findings

`merge_scan` scores the merged union with `build_evidence_summary(union, findings=None)` (`quirk/merge/scan.py:246`)
and returns that result's `rating` (`quirk/merge/scan.py:326`). The comment above the call says no band is ever
rendered from it, but the CLI prints it: `print(f"Score: {result['score']} ({result['rating']})")`
(`quirk/cli/sensor_cmd.py:960`). With no findings the CRITICAL/HIGH counts are zero, so neither the Phase 184.4 band
floor nor the scoring-v3 consequence ceiling can apply.

Probe (`.planning/phases/224-doc-claim-ledger-verification/work/probes/gc3-ops-G-sensor-merge-band-findingsless.sh`):
4 sensor TLS endpoints, one with an expired certificate. Real CLI merge -> `Score: 77 (GOOD)`. The same rows scored the
report way (`evaluate_endpoints` findings attached) -> `TLS certificate expired` CRITICAL, `29 POOR`,
"1 open CRITICAL finding — score limited to 29 (computed 85)".

The operators-guide now tells operators not to quote the merge band.

- [ ] Either drop the band from the merge CLI output, or derive findings for the union (as the dashboard does) and pass them.
- [ ] Add a test: a merged estate with an open CRITICAL must not print a band above the floor.

## Second surface: the Slack drift notification (added A3FIX, 2026-10-13)

`dispatch_notifications` (`quirk/notify/dispatcher.py:197`, `:225`) builds the `DriftSummary` from
`compute_trend_report`, whose `current_score` comes from `_score_for_session` (`quirk/intelligence/trends.py:275`,
`:217-219`: `build_evidence_summary(endpoints)` with no findings). `build_drift_summary` then maps that score to a band,
`score_band = _score_to_band(report.current_score)` (`quirk/notify/payload.py:133`, via `band_for_score` at `:103`), and
the Slack channel renders it: `Score Band: {summary.score_band}` (`quirk/notify/channels/slack.py:95`). Email and webhook
carry the score but no band.

The comment at `quirk/intelligence/trends.py:213-216` ("no caller of _score_for_session() ever reads a rating/band from
it, so a severity-blind evidence summary here can never diverge from a report band") is therefore false.

Probe (`.planning/phases/224-doc-claim-ledger-verification/work/probes/a3fix-notify-drift-band-findingsless-probe.py`,
isolated HOME/XDG): two sessions of 4 TLS endpoints, the current one with an expired certificate; the REAL
`dispatch_notifications` with a `[notifications]` Slack block (send captured in-process). Output:
`current_score=78 previous_score=84 score_band=LOW` (LOW = the GOOD band in notify vocabulary). The same session scored
the report way: `TLS certificate expired` CRITICAL, `32 POOR`, "1 open CRITICAL finding — score limited to 32
(computed 93)".

- [ ] Derive the drift band from a findings-aware score (shared fix with
      `261013-doc224-trend-and-merge-scores-skip-consequence-ceilings`), or drop `score_band` from the Slack header.
- [ ] Correct or delete the comment at `quirk/intelligence/trends.py:213-216`.
- [ ] When fixed, update `docs/operators-guide.md` §17 Troubleshooting ("Two surfaces show a band computed without findings").

## Feasibility & Effort

- **CONFIRMED** by the probe above and by reading `quirk/merge/scan.py:246` and `:326` and `quirk/cli/sensor_cmd.py:960`.
- **LIKELY** effort **S** to drop the band (one print line; `MergeLatestData` already has no rating field), **M** to score
  with findings (needs a config for `evaluate_endpoints`, which `merge_scan` does not take today). No spike needed.
- (A3FIX) **CONFIRMED** for the Slack surface by the live dispatch probe and by `quirk/notify/payload.py:103,133`,
  `quirk/notify/channels/slack.py:95`, `quirk/intelligence/trends.py:217-219`. Effort **S** to drop the band from the Slack
  header; **M** if fixed together with the trend-score todo (findings per session).
