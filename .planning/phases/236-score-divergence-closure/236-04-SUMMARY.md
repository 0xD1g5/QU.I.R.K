---
phase: 236-score-divergence-closure
plan: 04
subsystem: scoring / finding derivation
tags: [XSURF-09, legacy-tls, severity-divergence, fingerprint]
requires: [236-01, 236-02, 236-03]
provides:
  - "is_max_legacy_tls shared predicate (quirk/util/weak_crypto.py)"
  - "Two-tier legacy TLS on report and dashboard"
affects: [236-05, 236-08]
key-files:
  modified:
    - quirk/util/weak_crypto.py
    - quirk/engine/findings_evaluator.py
    - quirk/dashboard/api/finding_derivation.py
    - quirk/dashboard/api/finding_title_bridge.py
    - quirk/compliance/__init__.py
    - quirk/intelligence/remediation.py
    - tests/test_weak_crypto_helper.py
    - tests/test_ticketing_fingerprint_stability.py
    - tests/test_compliance_normalizer.py
    - tests/test_changelog_5280_section.py
    - tests/test_evidence_finding_vocabulary_parity.py
    - tests/test_finding_engine_parity.py
    - tests/test_finding_title_bridge.py
    - tests/test_compliance_title_join.py
decisions:
  - "D-01/D-20 two-tier legacy TLS from one shared predicate; D-05 dashboard titles kept; D-21 fingerprint alias"
metrics:
  tasks: 3
  completed: 2026-11-16
---

# Phase 236 Plan 04: Legacy TLS two-tier closure (XSURF-09) Summary

One shared `is_max_legacy_tls` predicate now drives a HIGH "max version is legacy" tier and a LOW "legacy offered alongside TLS 1.2+" tier on both the report and the dashboard; the "Legacy TLS version: " divergence is gone (SEVERITY_DIVERGENCES 8 -> 7).

## Commits
- 2d8d2d35 feat: predicate + report tiers + D-21 alias + constituency + normalizer tripwire (6->7 / 7->8)
- 045bd805 feat: dashboard tiers, bridge/reachability entries, divergence + `_DIVERGENCE_PHRASES` key removed, fingerprint regression test
- 6a751dff test: dependent-test updates, non-xfail compliance guard

## Results
- Residuals: before, `legacy_max_tls10` was a dashboard-HIGH vs report-LOW residual under "Legacy TLS version: ". After, none for `legacy_max_tls10`, `legacy_max_sslv3` (legacy key) and `legacy_offered_with_tls12`; `-k legacy` gate: 3 passed. `legacy_max_sslv3` stays listed under "Weak cipher suites enabled" (plan 05, untouched).
- Tests: 3 task verify sets green (58, 86, 106 passed + 1 xfail). Wide regression over every test importing scoring / findings_evaluator / Legacy TLS / finding_derivation / title_bridge: 1420 passed, 5 skipped, 4 xfailed, 1 failed (`tests/test_build_stamp.py::test_no_git_anywhere_returns_none`, a git-environment test unrelated to this change, not investigated further). `compileall` clean.
- Fingerprint stability: `test_max_legacy_title_keeps_legacy_tls_fingerprint` (1 test) proves new HIGH title == old title fingerprint via `TicketingChannel.compute_fingerprint` (the same call remediation_persist uses), with host and "Legacy TLS cipher suites accepted" counterweights. Existing fingerprints unchanged.

## D-18 score-effect hand-off
SCORING_VERSION stays 4.0 per D-18. Report scores DROP for endpoints whose max version is TLS 1.0/1.1 (LOW -> HIGH) and for SSLv2/SSLv3-only endpoints (previously no legacy finding at all). Dashboard: SSLv2/SSLv3-max endpoints gain a HIGH (previously none); endpoints offering TLS 1.0/1.1 with TLS 1.2+ gain a new LOW (previously no dashboard finding; not high-severity, small effect). Dashboard TLS 1.0/1.1-max HIGH is unchanged. Evidence `legacy_tls_count` is unchanged (signal-based, spans both tiers).

## expected_results entries affected (for plan 08)
- `quantum-chaos-enterprise-lab/expected_results_v4.md` line ~669 (`hygiene ... Legacy TLS versions present | -9`) and line ~817 prose: legacy-TLS severity is now HIGH for max-legacy endpoints, LOW only when TLS 1.2+ is also offered; verify the chaos-lab legacy-TLS hosts' tier and penalty.
- `quantum-chaos-enterprise-lab/scripts/gen_multihost_oracle_table.py:58` maps only the cipher-suite title; consider adding the new title.

## Deviations from Plan
1. [Rule 1 - plan assertion wrong] The acceptance check `slug_for_title(<finding title>) == 'legacy-tls-versions'` is invalid: `slug_for_title` looks up roadmap item titles (`REMEDIATION_KIND_SLUGS`), returns None for any finding title (old title included). The real fingerprint path is `REMEDIATION_CONSTITUENCY` (new title added) + `compute_fingerprint` (proven by the regression test).
2. [Rule 3] `test_compliance_normalizer.py` tripwire counts updated (alias 7->8, fingerprint 6->7), as the plan anticipated.
3. [Rule 1] `test_evidence_finding_vocabulary_parity.py` cross-check now unions both tier titles (the evidence counter is signal-based); `test_finding_title_bridge.py` canonical-title assertion repointed. No assertion loosened.
4. No separate COMPLIANCE_MAP entry needed: the alias normalizes to the old title's key (verified by the new non-xfail test). `last_verified` not touched.

## Known Stubs / Threat Flags
None.

## Self-Check: PASSED
Commits 2d8d2d35, 045bd805, 6a751dff exist; modified files present; SEVERITY_DIVERGENCES lacks "Legacy TLS version: " (gate green).
