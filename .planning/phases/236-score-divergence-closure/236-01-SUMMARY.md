---
phase: 236-score-divergence-closure
plan: 01
subsystem: scoring / cross-surface parity
tags: [xsurf-13, severity-divergence, behaviour-gate, mutation-proof]
requires: []
provides:
  - tests/fixtures/divergence_rows.py::FAMILY_ROWS (33 finding families)
  - tests/test_severity_divergence_behaviour.py (behaviour-derived gate, 43 nodes)
  - scripts/score_attribution.py::severity_multiset_diff
  - SEVERITY_DIVERGENCES reshaped (reason, todo, score_moving, side, families)
affects: [236-02, 236-03, 236-04, 236-05, 236-06, 236-07, 236-08]
tech-stack:
  added: []
  patterns: [run-time-derived gate, mutation proof on a temp copy of the derivation module]
key-files:
  created:
    - tests/fixtures/divergence_rows.py
    - tests/test_severity_divergence_behaviour.py
    - .planning/todos/pending/261115-kerberos-weak-etype-dashboard-only-score-divergence.md
    - .planning/todos/pending/261115-dnssec-dashboard-only-score-divergence.md
    - .planning/todos/pending/261115-http-mtls-pair-dashboard-only-score-divergence.md
  modified:
    - scripts/score_attribution.py
    - tests/test_score_attribution.py
    - tests/test_finding_title_bridge.py
    - tests/test_changelog_5280_section.py
    - quirk/dashboard/api/finding_title_bridge.py
    - .planning/LEDGER.md
key-decisions:
  - "Gate keys on (host, port, severity), not title (titles differ by design, D-05)."
  - "Kerberos weak-etype and DNSSEC dispositioned score_moving True with own todos and LEDGER rows (D-19); not fixed."
  - "The census extra (HTTP row + MTLS_REQUIRED sibling) is dispositioned the same way; plan 02 decides whether to fix it."
  - "No changelog.d fragment is created (D-18)."
requirements-completed: [XSURF-13]
duration: about 1h
completed: 2026-11-16
---

# Phase 236 Plan 01: Behaviour-derived severity-divergence gate Summary

A gate that runs both derivers on one fixture family at a time and diffs per-(host, port) HIGH/CRITICAL multisets in both directions, replacing the AST-literal gate. It found the four known divergences plus Kerberos, DNSSEC and one new extra, all now dispositioned.

## Commits

| Task | Commit | What |
|------|--------|------|
| 1 | 759ee1b7 | `FAMILY_ROWS` (33 families) + shared `severity_multiset_diff`; self-test still `6/6` |
| 2 | e63b4b5f | Behaviour gate, completeness self-check, mutation + blindness legs (every_residual nodes red by design until Task 3) |
| 3 | 5d18efab | `SEVERITY_DIVERGENCES` dispositions, old AST severity group removed, 3 todos + LEDGER rows |

## Census (measured, not targeted)

**10 residuals across 33 families** at HEAD 44c1955f. The four known divergences were a floor; the count is higher. Full output: `236-evidence/census-head.txt` (pre-disposition run; 10 `every_residual` nodes failed, as expected).

| Family | Side | host:port | Sev | Title | Disposition (SEVERITY_DIVERGENCES key) |
|---|---|---|---|---|---|
| legacy_max_tls10 | dashboard_only | 10.236.1.1:443 | HIGH | Legacy TLS version: TLSv1 | "Legacy TLS version: " |
| legacy_max_sslv3 | dashboard_only | 10.236.2.1:443 | HIGH | Weak cipher suites enabled | "Weak cipher suites enabled" (SSLv3 sets the weak-cipher flag; the dashboard has no legacy title for SSLv3, the report none either) |
| weak_cipher | dashboard_only | 10.236.4.1:443 | HIGH | Weak cipher suites enabled | "Weak cipher suites enabled" |
| ecdsa_192 | report_only | 10.236.5.1:443 | HIGH | TLS certificate uses undersized ECDSA key | "TLS certificate uses undersized ECDSA key" |
| container_openssl_111 | report_only | 10.236.11.1:0 | HIGH | End-of-life OpenSSL 1.1.x ... | "End-of-life " |
| container_openssl_102 | report_only | 10.236.12.1:0 | CRITICAL | End-of-life OpenSSL 1.0.x ... | "End-of-life " |
| container_pycrypto_old | report_only | 10.236.13.1:0 | HIGH | Severely outdated Python cryptography package | "Severely outdated Python cryptography package" |
| kerberos_rc4 | dashboard_only | 10.236.15.1:88 | HIGH | Kerberos weak etype: rc4-hmac | "Kerberos weak etype: " (D-19) |
| dnssec_none | dashboard_only | 10.236.16.1:53 | HIGH | DNSSEC: NONE | "DNSSEC: " (D-19) |
| http_on_tls_port_with_mtls_pair | dashboard_only | 10.236.31.1:443 | HIGH | Unencrypted HTTP service | "Unencrypted HTTP service" (extra) |

Clean families (no residual), proving both derivers agree there: rsa_1024, cert_expired, cert_near_expiry, tls_untrusted_ca, tls_self_signed, container_scan_error, dnssec_nsec, email_weak, broker, broker_tls_weak, plaintext_amqp, plaintext_redis, codesign, codesign_weak_alg, saml, saml_weak_encryption, saml_sha1, saml_oidc_rs256, plaintext_http, http_on_tls_port, jwks_verify_disabled, bearer_unsigned, legacy_offered_with_tls12.

SEVERITY_DIVERGENCES now has **8 entries**, all `score_moving: True`.

### Census extras

| Key | Side | Families | Firing conditions | Measured score (one-family rows: report / dashboard) | Todo |
|---|---|---|---|---|---|
| Unencrypted HTTP service | dashboard_only | http_on_tls_port_with_mtls_pair | Report: `findings_evaluator.py:434` `_postprocess_findings` rewrites "Plaintext HTTP service detected" to INFO "mTLS required" when the host:port is TLS-designated and a sibling TLS row has `tls_blocker_reason == MTLS_REQUIRED`. Dashboard: `scan.py:167` `findings_for_endpoint` HTTP branch judges the row alone and keeps HIGH. | 84 / 66 | 261115-http-mtls-pair-dashboard-only-score-divergence.md |

Measured one-family score pairs for the other residuals (report / dashboard, `build_evidence_summary` + `compute_readiness_score`, profile None): legacy_max_tls10 76/62; legacy_max_sslv3 77/63; weak_cipher 77/63; ecdsa_192 63/77; container_openssl_111 69/84; container_openssl_102 34/84; container_pycrypto_old 69/84; kerberos_rc4 82/68; dnssec_none 83/68. These are single-family measurements and are not the 76/31 and 76/63 figures quoted from RESEARCH for the Kerberos and DNSSEC probes; the todos record the measured values.

## Mutation proofs (D-08)

Mutations are applied to a temp copy of the derivation module, so the tree stays clean (`git diff` of `quirk/` empty after every run).

- M1: `_DNSSEC_WEAK_MAP` NSEC "MEDIUM" -> "HIGH" (family `dnssec_nsec`). M2: after the final statement of `findings_for_endpoint`, a loop rewriting the untrusted-CA finding to HIGH (family `tls_untrusted_ca`).
- Command: `.venv/bin/python -m pytest -v --basetemp=$PWD/.pytest-bt-audit/236-01 tests/test_severity_divergence_behaviour.py -k "mutation or blind or empty_dispositions" -p no:cacheprovider`
  Result: 6 passed: `test_injected_mutations_turn_new_gate_red[M1|M2]` (leg a, new gate red under injection, family clean unmutated), `test_gate_is_red_with_empty_dispositions[M1|M2]` (leg c, permanent non-vacuity), `test_old_ast_gate_is_blind_to_the_same_mutations[M1|M2]` (leg b, the retired gate's key set identical for original and mutated source).
- Live injection (real file edited, then reverted with `git checkout -- quirk/dashboard/api/routes/scan.py`): `sed` NSEC "MEDIUM" -> "HIGH", then `pytest -k "every_residual and dnssec_nsec"`: **1 failed**, message `dnssec_nsec: dashboard_only 10.236.17.1:53 HIGH 'DNSSEC: NSEC'`. After revert `git diff -- scan.py` empty.
- Pre-fix empty-ledger run at HEAD: with the old-shaped ledger (no side/families) every one of the 10 residuals was undispositioned, naming the four known keys plus the rest (see census-head.txt).
- Collected-node guard: `pytest --collect-only -q tests/test_severity_divergence_behaviour.py` = 43 tests; `-k "mutation or blind"` collects 4 (2 mutations x 2 tests), not 0.

## Deviations from Plan

**1. [Rule 1 - Bug in plan] M2 as specified is not blind to the old gate.** The plan's M2 (replace the untrusted-CA `severity="MEDIUM",` with `severity=_sev,`) removes the literal for a title that IS in `DASHBOARD_TITLE_BRIDGE`, so the old gate saw "dashboard [] vs report [MEDIUM]" and its key set changed (measured: `{'TLS certificate issued by untrusted CA'}` newly flagged). The old gate would have gone red there, by accident, for the wrong reason. M2 was reimplemented as a post-loop severity rewrite inside `findings_for_endpoint` (located with `ast`), which leaves every literal untouched, and the old gate is demonstrably blind to it. Same target family and same intent.
**2. [Plan wording] Parametrized legs.** The mutation and blindness tests are parametrized over M1/M2 (4 nodes for `-k "mutation or blind"`) instead of 2 single tests; the plan's "exactly 2 collected" assumed one node each.
**3. [Plan wording] Completeness extraction scoped to the call closure.** The plan said to scan "all functions in the file" for the dashboard derivation module. Today that file also holds motion, DAR and hardware routes that are not part of the scored derivation, so extraction follows the intra-file call closure from `derive_dashboard_finding_items`. It still follows the block when plan 03 moves it. It also covers variable-severity sites, `**kwargs` severity sites and in-place `f["title"]`/`f["severity"]` rewrites. `_COVERAGE_EXEMPT` is empty (every site is emitted by a family).
**4. [Extra families] 33 families instead of the plan's list**, adding `saml_weak_encryption`, `saml_sha1`, `saml_oidc_rs256` and `broker_tls_weak` because the completeness check named those title sites.
**5. [Extra todo] A third new todo and LEDGER row** for the census extra (D-09 default), beyond the two the plan names. LEDGER Open count 295 -> 298.

## Authentication gates
None.

## Known Stubs
None.

## Threat Flags
None. New files contain divergence evidence only; nothing sourced from `.planning/security-embargo/`.

## Notes for later plans
- D-18: no `changelog.d` fragment is created in this phase (`git ls-files changelog.d` = README.md only). Score-direction notes belong in LEDGER rows, phase SUMMARYs and the D-17 hand-off.
- `tests/test_changelog_5280_section.py::_DIVERGENCE_PHRASES` now has 9 keys equal to `set(SEVERITY_DIVERGENCES) | set(UNBRIDGED_DASHBOARD_TITLES)`; each later plan that deletes an entry must drop the matching key. README and CHANGELOG were not touched (D-17). The "Unencrypted HTTP service" key maps to the existing clause "Other findings may also differ".
- Each later fix plan must delete its `SEVERITY_DIVERGENCES` entry in the same change (the gate fails on a stale entry).
- `scripts/score_attribution.py::prefix_key` matches `SEVERITY_DIVERGENCES` keys by `startswith` on dashboard titles, so the "Unencrypted HTTP service" key coarsely attributes any dashboard-only plain-HTTP surplus. It is bounded by GAP-BOUND; it goes away when the extra is fixed.
- Verification run: `tests/test_severity_divergence_behaviour.py tests/test_finding_title_bridge.py tests/test_changelog_5280_section.py tests/test_score_attribution.py tests/test_ledger_completeness.py tests/test_backlog_reconciliation_gate.py tests/test_merge_scan.py` = 128 passed; plus `test_evidence_finding_vocabulary_parity`, `test_evidence_scoring_title_coverage`, `test_dashboard_scoring_findings`, `test_cross_surface_parity` = 38 passed; `python -m compileall -q quirk scripts tests` clean. No test failed.
- Documentation checklist: no CLI command, config option, API endpoint or report section changed in this plan; no docs or Obsidian sync owed here (later plans own D-15).

## Self-Check: PASSED
Files and commits verified below in the run (759ee1b7, e63b4b5f, 5d18efab; fixtures, gate, 3 todos present).
