---
phase: 236-score-divergence-closure
plan: 09
subsystem: dashboard findings derivation / divergence gate
tags: [xsurf-09, xsurf-13, gap-closure, scan_error, citruth-03]
requires: [236-01, 236-04, 236-07, 236-08]
provides:
  - "Dashboard findings_for_endpoint skips scan_error rows exactly as evaluate_endpoints does"
  - "Behaviour-gate families tls_scan_error_with_fields, http_scan_error and four parity-equal boundary families; mutation M3"
  - "LEDGER rows 261116-* plus pending todos for review findings WR-01, WR-03, WR-04/05, WR-07"
affects: [236-verification, 240]
key-files:
  modified:
    - quirk/dashboard/api/finding_derivation.py
    - tests/fixtures/divergence_rows.py
    - tests/test_severity_divergence_behaviour.py
    - tests/test_cross_surface_parity.py
    - docs/report-interpretation.md
    - docs/UAT-SERIES.md
    - docs/uat-coverage-gaps.md
    - .planning/LEDGER.md
decisions:
  - "Guard sits after the JWKS advisory block and before the HTTP block, an exact mirror of the report's order; no dashboard copies of the report's MEDIUM/INFO scan-error findings (score-neutral, would be a D-05 vocabulary change)"
  - "rsa_size_0 / rsa_pss_1024 (WR-03) not added to FAMILY_ROWS; ledgered instead"
metrics:
  tasks: 4
  completed: 2026-11-16
---

# Phase 236 Plan 09: scan_error guard parity (XSURF-09 gap closure) Summary

The dashboard deriver now sends every endpoint row with a truthy `scan_error` out before the HTTP and TLS checks, as the report's `evaluate_endpoints` does, so a TLS 1.0 row whose fallback scan failed after the handshake scores the same on both surfaces.

## Commits

- `56e2395a` test(236-09): add scan_error and boundary divergence families (RED)
- `e13b62f8` fix(236-09): skip scan_error rows in the dashboard deriver as the report does (XSURF-09)
- `e6f81a96` docs(236-09): ledger rows for open Phase 236 review findings
- `1a3d1a86` docs(236-09): UAT-236-07, report-interpretation note, regenerated gaps
- plus the final plan-metadata commit (SUMMARY, STATE, ROADMAP, evidence)

## RED and GREEN evidence

- RED (236-evidence/gap-09-red.txt, RED commit `56e2395a`, finding_derivation.py untouched there): `CENSUS (measured): 6 residual(s) across 39 families`; `test_every_residual_is_dispositioned[tls_scan_error_with_fields]` and `[http_scan_error]` FAILED with undispositioned dashboard-only HIGH residuals (Legacy TLS / self-signed; Unencrypted HTTP service).
- GREEN (gap-09-green.txt): `CENSUS (measured): 3 residual(s) across 39 families` (kerberos_rc4, dnssec_none, http_on_tls_port_with_mtls_pair, the unchanged set); 65 passed in the gate plus parity files.
- Headline for tls_scan_error_with_fields (two healthy rows plus the family): pre-fix report 73, dashboard 60; post-fix report 73 == dashboard 73, HIGH 0/0, CRITICAL 0/0 (pinned in `test_xsurf236_scan_error_tls_row_headline_parity`). The verifier's single-row probe measured 74 vs 61.
- Mutation M3 (guard text replaced by `if False:`): `test_injected_mutations_turn_new_gate_red[M3_drop_scan_error_guard]`, `test_gate_is_red_with_empty_dispositions[M3_drop_scan_error_guard]` and `test_old_ast_gate_is_blind_to_the_same_mutations[M3_drop_scan_error_guard]` all PASSED (the old AST gate is blind to M3, as expected). No exclusion was needed.

## Boundary families

Added: tls_scan_error_with_fields, http_scan_error, legacy_inconsistent_max, legacy_supported_only, ecdsa_256, rsa_2048. The four boundary ones had zero residuals before and after the fix, so none was dropped. rsa_size_0 and rsa_pss_1024 diverge today (WR-03), so they are not families; see ledger below. No SEVERITY_DIVERGENCES entry was added or changed.

## New LEDGER IDs

261116-rsa-undersized-key-predicate-differs-across-surfaces (P2, WR-03), 261116-legacy-tls-count-ignores-ssl-max-tier (P3, WR-01), 261116-max-legacy-tls-missing-version-falls-to-low-tier (P3, WR-07, names the `is_max_legacy_tls(None, ...)` predicate-level lock and does not rely on the legacy_supported_only family), 261116-divergence-gate-title-blind-and-disposition-absorbs-residuals (P3, WR-04/05). Open count 299 -> 303. No row was added for the report-only MEDIUM/INFO scan-error findings: the dashboard already emits INFO rows for scan_error protocols in `routes/scan.py` (~:213-252), so that observation is recorded here instead.

## Deviations from Plan

None in code. Notes: the closure-pending staging and the 236-08 SUMMARY "Closure pending merge" section were updated (XSURF-09/13 commit lists, the two new test nodes, the score-movement clause); LEDGER row 261115-phase236-post-merge-closure cites 56e2395a and e13b62f8. REQUIREMENTS.md untouched, every XSURF box stays `[ ]`. Phase 236 SUMMARY-tracked files are force-added; evidence files other than gap-09 are untracked by design.

Score-movement note: dashboard scores rise for TLS or HTTP rows whose scan errored after populating columns (they no longer raise dashboard HIGH/CRITICAL findings, matching the report). Consequence for `routes/storyline.py` `finding_by_id_and_title`: it now returns `(ep, None)` for TLS titles on errored rows. That is intended and matches the report, which raises no such finding.

Docs: `docs/report-interpretation.md` gets one sentence; vault synced (`sync_vault_guides --check` exit 0, UAT-Series.md and the Phase-236 note updated). Lab-oracle check: `grep -rn "dashboard\b.*scan_error\|errored row" labs/*/expected_results.md quantum-chaos-enterprise-lab/expected_results_*.md` returned nothing, so no oracle change. UAT-236-07 added and PASS; `docs/uat-disposition-ledger.jsonl` needed no row (same as 236-08); `uat-coverage-gaps.md` regenerated. README, CHANGELOG, changelog.d and master guide unchanged.

## Verification

- Targeted: gate, parity, derivation consumers (200 passed); ledger gates (22 passed); doc, UAT and vault gates (187 passed, then the vault test passed after `--write`).
- Full local suite (background, `--basetemp` on /Volumes/Digs-1TB): `9234 passed, 42 skipped, 71 xfailed, 5 xpassed, 0 failed` in 25m53s.
- CI: see `236-evidence/branch-ci.json` (written verbatim from `branch_ci_state.py --branch v529-open --compare-main` after the final push and dispatch). branch-ci.json is untracked, so recording it does not move HEAD. The phase-close commit must sit directly on that head_sha; any later commit (STATE, ROADMAP, SUMMARY) moves HEAD past it and requires re-push, re-dispatch and re-observation (CITRUTH-03, `check_ci_truth`).

## Self-Check: PASSED (files and commits verified present)
