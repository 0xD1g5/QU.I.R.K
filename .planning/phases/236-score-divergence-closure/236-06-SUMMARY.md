---
phase: 236-score-divergence-closure
plan: 06
subsystem: scoring / finding derivation
tags: [XSURF-12, XSURF-14, container, severity-divergence]
requires: [236-01, 236-03, 236-05]
provides:
  - "evaluate_container_endpoints shared helper (report's own _evaluate_container_package; scan_error skip; dedupe)"
  - "Dashboard container crypto-library findings with report titles/severities"
  - "Pass A replay after: report 27 == dashboard 27"
affects: [236-08]
key-files:
  modified:
    - quirk/engine/findings_evaluator.py
    - quirk/dashboard/api/finding_derivation.py
    - quirk/dashboard/api/finding_title_bridge.py
    - tests/test_changelog_5280_section.py
    - tests/test_dashboard_scoring_findings.py
    - tests/test_derive_report_findings.py
  created:
    - .planning/phases/236-score-divergence-closure/236-evidence/passA-after.txt
    - .planning/phases/236-score-divergence-closure/236-evidence/passA-attribution-after.txt
decisions:
  - "D-06: report path untouched (evaluate_endpoints inline CONTAINER branch kept); helper used only by the dashboard, so no double count (pinned by test)"
  - "Adapter sets protocol=\"CONTAINER\" (the evaluator dict has no protocol key)"
metrics:
  tasks: 2
---

# Phase 236 Plan 06: Container findings on the dashboard Summary

The dashboard now derives container crypto-library findings through the report's own evaluator via `evaluate_container_endpoints`, and the Pass A real-data replay moves from report 27 / dashboard 42 to 27 / 27.

## Results
- SEVERITY_DIVERGENCES: 5 -> 3. Removed "End-of-life " and "Severely outdated Python cryptography package" and their `_DIVERGENCE_PHRASES` keys. Remaining: "Kerberos weak etype: ", "DNSSEC: ", "Unencrypted HTTP service".
- Container family residuals (behaviour gate) before -> after: container_openssl_111 1 -> 0, container_openssl_102 1 -> 0, container_pycrypto_old 1 -> 0; container_scan_error 0 -> 0 on both surfaces.
- `_OPENSSL_EOL` is not copied; `finding_derivation.py` stays FastAPI-free (minimal-import tests green).

## Pass A (snapshot replay, 56 endpoints)
| | before | after |
|---|---|---|
| report | 27 (CRIT 2, HIGH 8) | 27 (CRIT 2, HIGH 8) |
| dashboard | 42 (CRIT 0, HIGH 6) | 27 (CRIT 2, HIGH 10) |
| report-only residuals | 6 container | 0 |
| dashboard-only residuals | 2 DNSSEC NONE | 2 DNSSEC NONE (dispositioned D-19, masked by the CRITICAL ceiling) |

Headline scores are equal; the dashboard's HIGH count is 10 vs 8 because of the two DNSSEC residuals only.

Attribution after (`passA-attribution-after.txt`): `SCORES intel=27 html=27 dashboard=27`, `SCORE-PARITY: equal`. The script prints no UNATTRIBUTED lines at equal scores (50 before). Input caveat: the Pass A `latest.json` predates the fix, so the dashboard JSON was `latest.json` plus the 11 container FindingItems from the post-fix derivation of the snapshot and `score.score` set to the replay's 27 (scratch file, not committed). Only container rows were refreshed, so legacy-TLS/weak-cipher/ECDSA were not re-derived in that file; the replay (which uses the live derivers) is the authoritative evidence.

## D-18 score-effect hand-off (for docs / plan 08)
Dashboard scores drop for scans with end-of-life crypto libraries in container images (OpenSSL 1.0.x CRITICAL, 1.1.x HIGH, old Python cryptography HIGH). The Findings page gains one row per container crypto package (mostly LOW, not score-moving). Reproduced: 42 -> 27 on the Pass A data.

## Tests
- 148 passed over the plan verify list plus minimal-import and score-attribution tests; 1430 passed, 9 deselected, 4 xfailed over all 91 test files importing scoring / findings_evaluator / finding_derivation / finding_title_bridge / derive_dashboard (run before the protocol tag fix, plan verify list re-run after). compileall clean. No CBOM golden diffs needed.
- New: container titles/severity parity with report, scan_error yields none on both surfaces, dedupe parity (openssl + libssl1.1), protocol tag, no double count in `derive_report_findings`.
- Item-id: container rows have `id=None` (as the protocol-service adapter), so no `(id, title)` lookups can resolve them; unchanged lookups green (storyline, merge, trends tests).

## Affected oracle entries (plan 08 owns)
`quantum-chaos-enterprise-lab/expected_results_v4.md`, `expected_results_v3.md` (container image-old-libssl / image-mixed / image-old-pycrypto findings now appear on the dashboard too), `docs/chaos-lab.md`, `docs/UAT-SERIES.md`, `docs/doc-claim-ledger.jsonl` (doc-claim anchors). No `labs/*/expected_results.md` entry mentions container-library EOL.

## Deviations
- [Rule 1 - Bug] First adapter draft used `d.get("protocol")`, which is None for container dicts; changed to the literal "CONTAINER" (commit bd2d6c6a).
- Hand-edited STATE.md only (Current Position, last_activity, progress).

## Commits
- 8a414dca feat(236-06): shared evaluator + dashboard adapter + divergence removal
- bd2d6c6a fix(236-06): protocol CONTAINER tag
- 2dd285fc docs(236-06): Pass A after evidence

## Self-Check: PASSED (files and commits exist; replay output read directly)
