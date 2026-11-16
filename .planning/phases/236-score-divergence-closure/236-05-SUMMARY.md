---
phase: 236-score-divergence-closure
plan: 05
subsystem: scoring / finding derivation
tags: [XSURF-10, XSURF-11, weak-cipher, ecdsa, severity-divergence]
requires: [236-01, 236-03, 236-04]
provides:
  - "Report HIGH 'Weak TLS cipher suites accepted' bridged to dashboard 'Weak cipher suites enabled'"
  - "Dashboard HIGH 'TLS certificate uses undersized ECDSA key' (<256 bits), no Quantum- finding for that row"
affects: [236-08]
key-files:
  modified:
    - quirk/engine/findings_evaluator.py
    - quirk/dashboard/api/finding_derivation.py
    - quirk/dashboard/api/finding_title_bridge.py
    - quirk/compliance/__init__.py
    - quirk/intelligence/remediation.py
    - tests/test_changelog_5280_section.py
    - tests/test_dashboard_finding_storyline.py
    - tests/test_finding_engine_parity.py
    - tests/test_finding_title_bridge.py
decisions:
  - "D-02: separate HIGH site on tls_weak_ciphers_present, independent of LOW legacy-suites (T-236-10)"
  - "D-04: ECDSA <256 HIGH on dashboard, Quantum- skipped for that row; D-05 no renames"
  - "Remediation theme chosen: legacy-tls-versions (fingerprint tuple)"
metrics:
  tasks: 2
  commits: 1
---

# Phase 236 Plan 05: Weak cipher HIGH and undersized ECDSA HIGH Summary

Report now emits HIGH "Weak TLS cipher suites accepted" on `tls_weak_ciphers_present`; the dashboard emits HIGH "TLS certificate uses undersized ECDSA key" for ECDSA keys under 256 bits. Both divergences are closed.

## Results
- SEVERITY_DIVERGENCES: 7 -> 5 (removed "Weak cipher suites enabled", "TLS certificate uses undersized ECDSA key"); UNBRIDGED "Weak cipher suites enabled" removed; `_DIVERGENCE_PHRASES` keys removed together.
- Residuals (behaviour gate) before -> after: weak_cipher 1 -> 0, legacy_max_sslv3 1 (weak-cipher part) -> 0, ecdsa_192 1 -> 0.
- Bridge: "Weak cipher suites enabled" -> "Weak TLS cipher suites accepted" (reachability "specific", in legacy-tls-versions constituency); undersized ECDSA identity bridge (reachability "catchall-only"). Compliance entry copies "Weak cipher suite on email TLS endpoint" controls verbatim, no last_verified change.
- UNBRIDGED "Quantum-" reason now says the remaining finding is MEDIUM and "not score-moving".
- Tests: 1606 passed, 5 xfailed, 1 xpassed over all importers of finding_derivation/findings_evaluator/finding_title_bridge/scoring plus the plan's verify lists; compileall clean.

## D-18 score-effect hand-off
Report scores drop for endpoints accepting RC4/3DES/NULL/EXPORT/MD5 suites or SSLv2/SSLv3 (new HIGH; e.g. one such endpoint previously 84 report vs 69 dashboard). Dashboard scores drop for ECDSA keys under 256 bits (MEDIUM -> HIGH). SCORING_VERSION stays 4.0 (operator amendment).

## D-17 note for Phase 240
`_DIVERGENCE_PHRASES["Quantum-"]` keeps the "undersized ECDSA" phrase (5.28.0 text is historical); Phase 240 must re-point it when the README wording is removed.

## For plan 08 (expected_results)
No lab oracle names the new titles. Affected by the new HIGH: labs/email/expected_results.md (lines ~86, 105-109, 134, weak-cipher dedup discussion: generic TLS site now also emits "Weak TLS cipher suites accepted" HIGH on same host:port, distinct title) and labs/broker/expected_results.md (lines ~59-83, HIGH count 6 may gain generic weak-cipher HIGH on TLS ports 29093/25671/26380). Verify against a live lab before editing.

## Deviations from Plan
- Two tasks committed as one commit: the bridge, divergence and changelog-phrase edits are shared across both tasks and the behaviour gate only passes with both applied.
- tests/test_compliance_title_join.py and tests/test_compliance_normalizer.py needed no edits (assertions/tripwires did not move); the join test's emitted-title check is xfail (TRIAGE-149), unchanged.
- tests/test_finding_title_bridge.py: the "Weak cipher suites enabled is None" assertion flipped to assert the bridge; test_dashboard_finding_storyline unbridged exemplar repointed to a Quantum- title (Ed25519).
- CBOM golden fixtures: no cipher/ECDSA finding severities found in tests/fixtures; not regenerated.

## Self-Check: PASSED
Commit 6c4f24d1 exists; SEVERITY_DIVERGENCES length 5 verified live.
