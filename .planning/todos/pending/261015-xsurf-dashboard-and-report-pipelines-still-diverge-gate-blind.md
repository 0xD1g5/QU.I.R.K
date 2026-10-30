---
type: todo
created: 2026-10-15
source: Phase 228 code review (.planning/phases/228-cross-surface-score-parity/228-REVIEW.md), WR-01 + WR-02
priority: high
area: quirk/dashboard/api/routes/scan.py (_derive_identity_findings), tests/test_finding_title_bridge.py (_severity_divergence_keys), quirk/notify/dispatcher.py:197
status: pending
resolves_phase: null
owner: "999.132"
---

# The dashboard and report finding pipelines still disagree, the severity gate cannot see it, and the Slack drift score inherits it

Probe (228-REVIEW): 3 healthy TLS rows + 1 Kerberos row with `service_detail="etype:23:rc4-hmac:CRITICAL"` scores **80** via `derive_report_findings` and **32** via `derive_dashboard_scoring_findings` (reproduced in `tests/test_merge_scan.py::test_persisted_merge_score_is_independent_of_entry_point`, whose non-vacuity leg asserts they differ: 73 vs 30 on its fixture).

- WR-01: `_severity_divergence_keys` reads only literal `severity="..."` keywords inside `findings_for_endpoint`, so Kerberos weak-etype and DNSSEC findings (variable severity, `_derive_identity_findings`) and report-only HIGH/CRITICAL titles are never examined. `SEVERITY_DIVERGENCES` reads as complete but is not. Fix: derive divergences from behaviour (fixture row per protocol, run both derivers, diff HIGH/CRITICAL multisets both ways).
- WR-02: the Slack drift score (`compute_trend_report(current_ts, previous_ts, db)`, report deriver) and the dashboard Trends page it links to (dashboard deriver) can show different scores and bands for the same sessions. `tests/test_notify_dispatcher.py::test_dispatcher_trend_call_stays_three_positional_args` locks the split.

Why not fixed in 228: the dashboard deriver lives in `quirk/dashboard/api/routes/scan.py`, which imports `fastapi` (the optional `[dashboard]` extra) at module top. Notify runs from `quirk/cli/scheduler_cmd.py:422` and `quirk/scanner/hardware_drift.py:489` without that extra. The fix is either converging the pipelines or extracting the derivation (~`scan.py:110-670`) into a FastAPI-free module, which also closes the review's router-module Info item.

Deferred by the operator at Phase 228 close (2026-10-15): CR-01, WR-07 fixed in-phase (dab89ffc, 3b1d286c);
this item was triaged out of Phase 228's scope. Full evidence and the suggested fix are in the review section named
in `source`.
