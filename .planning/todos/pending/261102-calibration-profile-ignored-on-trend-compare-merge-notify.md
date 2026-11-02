---
type: todo
created: 2026-11-02
source: v5.28 milestone audit (.planning/milestones/v5.28-MILESTONE-AUDIT.md), gsd-integration-checker seam 1 WARNING (XSURF-07, SCORE-09); confirmed in source by the audit
priority: medium
area: quirk/dashboard/api/routes/trends.py, quirk/dashboard/api/routes/scan.py (compare), quirk/dashboard/api/routes/merge.py, quirk/intelligence/trends.py, quirk/cli/sensor_cmd.py
status: pending
resolves_phase: null
owner: "999.131"
---

# Calibration profile is applied to the headline score only; trend, compare, merge and notify always score as "balanced"

**Filed:** 2026-11-02 (v5.28 milestone audit; the cross-phase integration check found it, and the audit re-read each call site)
**Priority:** medium. With the default profile, every surface agrees. With a strict or lenient profile, the headline and the other surfaces disagree.
**Sibling:** `261013-doc224-dashboard-score-ignores-calibration-overrides-and-scan-profile.md` (also 999.131) covers only the **headline** half: `calibration_overrides` are ignored, and the newest run's profile is applied to every scan. This todo is the other half, the surfaces that pass no profile at all.

## The defect

`compute_readiness_score(evidence, profile=None)` (`quirk/intelligence/scoring.py:464-467`) defaults to "balanced".
`PROFILE_MULTIPLIERS` (strict 1.4×, lenient 0.7×, `scoring.py:166-170`) still apply under scoring 4.0.

The surfaces resolve the profile in three different ways:

| Surface | Call site | Profile passed |
|---|---|---|
| Dashboard headline | `routes/scan.py:1887` | `profile=stored_profile` (newest intelligence file) |
| Scan history | `routes/scan.py:1617` | `ScanJob.calibration` |
| Trend timeline | `routes/trends.py:153` | none, so "balanced" |
| Compare | `routes/scan.py:2127-2128` | none |
| `/api/merge/latest`, overall and per-segment | `routes/merge.py:95`, `:121` | none |
| Notify / drift | `quirk/intelligence/trends.py:278` | none |
| `quirk sensor merge` | `quirk/cli/sensor_cmd.py:1013` | none |

So for a scan run with `--profile strict` or `lenient`, the newest trend point, the compare view and the merge gauge do not equal the headline. Drift notifications can also fire on a profile change rather than a posture change.

Phase 228's parity tests run under the default profile, which is why they are green.

## Fix shape (not sized)

- Resolve one profile per scan session.
- Pass it on every `compute_readiness_score` call that scores a stored session.
- Add a parity test that runs the cross-surface comparison under `strict` as well as `balanced`.
- Decide what a merge should use when its sensors were scanned with different profiles.
