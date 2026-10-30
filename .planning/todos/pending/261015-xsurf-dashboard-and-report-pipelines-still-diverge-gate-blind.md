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

## Feasibility & Effort

Added 2026-10-30 (Phase 235 plan 16, D-30 GO precondition a). Every site below was re-located by grep at v5.28.0 (tree of
`efc0bb56`), not copied from the planning-time list.

**Feasibility: LIKELY.** The code supports the second of the two fix shapes above (extract the dashboard derivation into a
FastAPI-free module) better than the first (converge the two pipelines), and the first is only reachable per divergence, not as
one change.

- The dashboard recipe is already router-free in intent: `derive_dashboard_finding_items` (`quirk/dashboard/api/routes/scan.py:402`)
  says so in its docstring, yet the module imports `fastapi` at `scan.py:11`, so nothing outside the `[dashboard]` extra can
  import it. The recipe is `findings_for_endpoint` (`scan.py:121`), `_derive_findings` (`:372`), `derive_dashboard_finding_items`
  (`:402`), `derive_dashboard_scoring_findings` (`:440`) and `_derive_identity_findings` (`:475`), a contiguous block ending before
  `_derive_motion_findings` (`:588`). Its output types, `FindingItem` and `IdentityFinding`, come from
  `quirk/dashboard/api/schemas.py:131`, which does not import fastapi (grep: no match), so the block has no hard FastAPI dependency.
- Dashboard-side consumers of that block: `quirk/dashboard/api/routes/trends.py:22,67,76`, `routes/merge.py:24,94,119`,
  `routes/scan.py:2125-2126`. Report-side: `derive_report_findings` (`quirk/engine/findings_evaluator.py:1373`), used by
  `quirk/merge/scan.py:34-36` and as the default deriver in `quirk/intelligence/trends.py:258-260`
  (`compute_trend_report(..., findings_deriver=None)`, `trends.py:286`).
- WR-02 site: `quirk/notify/dispatcher.py:188` calls `compute_trend_report(current_ts, previous_ts, db)` with the default
  (report) deriver, reached from `quirk/cli/scheduler_cmd.py:422`; the Trends page passes the dashboard deriver. The split is locked
  by `tests/test_notify_dispatcher.py:595` (`test_dispatcher_trend_call_stays_three_positional_args`).
- WR-01 site: `tests/test_finding_title_bridge.py:465` (`_severity_divergence_keys`) builds the gate's set from an AST read of
  literal severities, and its dashboard side is `_ast_title_severity_sites(_SCAN_PY, "findings_for_endpoint")`, so identity findings
  (Kerberos weak etype, DNSSEC; variable severity from `_derive_identity_findings`, `scan.py:475`) are never examined. The declared
  sets are `UNBRIDGED_DASHBOARD_TITLES` (`quirk/dashboard/api/finding_title_bridge.py:148`) and `SEVERITY_DIVERGENCES` (`:213`);
  `canonical_cli_title` is `:280`.
- The live proof the two pipelines differ is `tests/test_merge_scan.py:663`
  (`test_persisted_merge_score_is_independent_of_entry_point`), whose non-vacuity leg asserts 73 vs 30 on its fixture.

**Effort: L overall**, three independent parts that share one instrument:

1. WR-01, a behaviour-derived divergence gate. **M.** One fixture row per protocol, run both derivers, diff the HIGH/CRITICAL multisets
   both ways, replace the AST read. `scripts/score_attribution.py` already does the per-scan version of the comparison.
2. WR-02, the Slack/Trends split. **M** for the extraction (about 470 lines move; tests that monkeypatch names on
   `quirk.dashboard.api.routes.scan` need a re-export), then **S** to pass the dashboard deriver from the dispatcher. This makes Slack and
   the Trends page agree with each other. It does not make the dashboard agree with the report.
3. The four score-affecting divergences, each its own todo: legacy-TLS severity **S** to **M**, weak-cipher suites **M**,
   undersized ECDSA **S-M**, container-library EOL **S-M** (sizes from those todos' own sections). Only this part moves the
   dashboard and report scores toward each other.

**Unknowns.** (a) Whether the Kerberos weak-etype and DNSSEC variable-severity findings need a scoring decision rather than a
bug fix: the todo set treats them as a divergence but nobody has decided which surface is right. (b) How many real divergences the
behaviour-derived gate finds beyond the 4 code keys and 21 todo lines that the run-time sweep classified into 8 score-divergence rows.
(c) Whether moving the block breaks tests that patch `quirk.dashboard.api.routes.scan.*`.

**Spike: yes, short.** Build the WR-01 instrument first and run it once; it sizes unknown (b) and is plan 1 of the scheduled phase
anyway, so it is not a separate pre-phase.

**Measured gap, dated.** On the core chaos-lab profile the gap was **zero**: 2026-10-29 pre-release measurement at `d3189d12` gave
intelligence JSON 28, HTML report 28, dashboard `/api/scan/latest` 28 (headline equal, nothing to attribute). The published 5.28.0
smoke on 2026-10-30 gave 30/30/30 on macOS and on the contributor clone, and 27/27/27 on Linux Python 3.10 and 3.11, again with an empty
attributed set. The absolute number differs by host (27 to 30) but the three surfaces agreed within every run. The divergence is
real only on targeted probes: 80 (report) vs 32 (dashboard) for three healthy TLS rows plus one Kerberos RC4 row, 73 vs 30 on the
merge fixture, and 84 vs 69 for a single weak-cipher endpoint. The core lab simply does not contain those findings.

Scheduled: ROADMAP.md "Next Milestone Candidates (v5.29)", Phase 236 (v5.29 candidate, early): Dashboard/Report Score Divergence
Closure, which carries the four score-affecting todos; the gate and Slack/Trends parts (items 1 and 2 above) are referenced from there
and are not yet planned as separate work.
