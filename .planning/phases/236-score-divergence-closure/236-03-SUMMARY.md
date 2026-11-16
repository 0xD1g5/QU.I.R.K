---
phase: 236-score-divergence-closure
plan: 03
subsystem: dashboard-derivation / notify
tags: [refactor, notify, fastapi-free, replay]
requires: [236-01, 236-02]
provides: [quirk.dashboard.api.finding_derivation, notify drift on dashboard recipe, Pass A baseline]
affects: [quirk/notify/dispatcher.py, routes/scan.py, trends, merge, storyline]
key-files:
  created:
    - quirk/dashboard/api/finding_derivation.py
    - tests/test_finding_derivation_minimal_import.py
    - .planning/phases/236-score-divergence-closure/236-evidence/passA_replay.py
  modified:
    - quirk/dashboard/api/routes/{scan,trends,merge,storyline}.py
    - quirk/notify/dispatcher.py
    - tests/test_notify_dispatcher.py
    - tests/test_browser_e2e_harness_clock.py
    - tests/test_finding_title_bridge.py
    - tests/test_finding_engine_parity.py
    - tests/fixtures/chaos_lab_findings.py
    - tests/test_pqc_terminology_gate.py
metrics:
  tasks: 3
  commits: 3
requirements: [XSURF-13, XSURF-14]
---

# Phase 236 Plan 03: FastAPI-free derivation module, notify on dashboard recipe, Pass A baseline

One-liner: the dashboard finding derivation block moved verbatim into a FastAPI-free module, the Slack drift score now uses the dashboard deriver, and a snapshot replay records the pre-fix Pass A headline (report 27 vs dashboard 42).

## Commits
- `7ed02587` refactor: extract derivation block, re-export, repoint consumers/tests, minimal-import test
- `b4a425a5` feat: dispatcher passes `findings_deriver=derive_dashboard_scoring_findings`; parity test
- `e621fa68` docs: Pass A replay script + before artifacts

## Census before/after
`SEVERITY_DIVERGENCES` has 8 entries before and after (no edit). Gate `tests/test_severity_divergence_behaviour.py`: 43 passed before and after. `_COVERAGE_EXEMPT` stays `{}`. The gate resolves its derivation file via `inspect.getsourcefile(findings_for_endpoint)`, so its closure walk and temp-copy mutation tests follow the block into `finding_derivation.py` with no edit.

## Patch-target audit (patch-targets-before/after.txt)
Only routes.scan hits whose name is moved or used by the moved block: `tests/test_browser_e2e_harness_clock.py` `setattr(scan_mod, "datetime", frozen)` -> repointed to `finding_derivation`, plus an in-test `assert derivation_mod.datetime is frozen` and a run-time `past-120d` case. Other routes.scan patches (`_default_db_path`, `load_scan_coverage`, `_detect_crypto_bridges`, `compute_item_lifts`, `compute_projected_score`) target names that stayed in scan.py: no change. The after-file differs from before only in that one test's lines.

Clock proof: with the patch reverted to routes.scan and the assertion removed, `pytest -k past-120d tests/test_browser_e2e_harness_clock.py` FAILED ("Certificate expired"); restored, it passes (1 passed).

## Minimal-import proof
`tests/test_finding_derivation_minimal_import.py` (7 tests): subprocess with a MetaPathFinder blocking fastapi/starlette/uvicorn; combined chain (dispatcher first, hardware_drift, scheduler_cmd, finding_derivation), single imports, a self-check that the blocker really blocks, and a dispatch-path test driving `dispatch_notifications`. Mutation: adding `from quirk.dashboard.api.middleware.auth import require_auth` to finding_derivation.py turned 3 of the 7 red (chain, single derivation, dispatch path); restored, 7 pass.

## Trends parity
`test_dispatcher_score_matches_trends_page_trends_parity`: Slack score 67 == /api/trends 67 on the same DB (Kerberos RC4 + DNSSEC NONE rows); default deriver differs (non-vacuity). Mutation: removing the kwarg gave `81 == 67` red. `test_dispatcher_trend_call_passes_dashboard_deriver` replaces the old three-positional-args AST test.

## Pass A baseline (D-12, D-22) — from a sqlite `.backup` snapshot
Original DB mtime unchanged (1794103431 before and after).
- report: score 27, CRITICAL=2, HIGH=8, "2 open CRITICAL findings — score limited to 27 (computed 78)"
- dashboard: score 42, CRITICAL=0, HIGH=6, "6 open HIGH findings — score limited to 42 (computed 78)"
- dashboard-only residuals: 2x DNSSEC: NONE (HIGH). report-only: 6 container-image findings (2 CRITICAL EOL OpenSSL 1.0.x, 2 HIGH EOL OpenSSL 1.1.x, 2 HIGH outdated cryptography 2.9.2).
- `score_attribution.py` (passA-attribution-before.txt): exit 1, `SCORES: intel=27 html=27 dashboard=42`, `SCORE-STRICT PASS`, `SCORE-PARITY: FAIL unattributed`. It lists the container EOL/outdated items as UNATTRIBUTED (dashboard absent, report CRITICAL/HIGH), plus many other lower-severity UNATTRIBUTED rows (Cisco hardware advisory, MYSQL/POSTGRESQL encryption posture HIGH dashboard-only, SMTP/IMAP/POP3 TLS endpoint LOW, etc.). DNSSEC NONE is not listed (dispositioned). Recorded verbatim, not assumed.

## Deviations
1. **[Rule 3 - Blocking] Dispatcher imports the deriver at call time, not module level** (plan said module level). `tests/test_notify_session_identity.py::test_import_hygiene_no_fastapi_or_pydantic` (Phase 229) forbids pydantic after importing `quirk.notify.dispatcher`; finding_derivation pulls pydantic via dashboard schemas, and the module-level import turned that test red. Pydantic is installed transitively (sslyze), so only import cost is at stake. A local import keeps that gate green, and a dispatch-path subprocess test (fastapi blocked) covers the lazy import so the T-236-DoS mitigation is not lost. The AST test and acceptance grep still match.
2. `passA_replay.py` inserts cwd into `sys.path`: the plan's `python -I` ignores PYTHONPATH.
3. `scan.py` keeps now-unused imports (`ADVISORY_JWKS_VERIFY_DISABLED`, `_chain_verified`, etc.) to keep the diff minimal and not break any importer.

## Doc impact
No CLI, config, endpoint or report change; no doc/Obsidian updates required for this plan.

## Known Stubs
None.

## Self-Check: PASSED (files and commits verified on disk; 200 passed, 1 xfailed across the touched and gate test files)
