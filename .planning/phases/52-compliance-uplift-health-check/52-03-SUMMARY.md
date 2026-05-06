---
phase: 52-compliance-uplift-health-check
plan: "03"
subsystem: compliance
tags: [compliance, soc2, iso27001, python, tdd]
dependency_graph:
  requires: [52-01]
  provides: [_soc2, _iso, _PHASE_52_VERIFIED, _SOC2_CC_URL, _ISO_27001_URL, SOC2-CC-entries, ISO-27001-entries]
  affects: [quirk/compliance/__init__.py, tests/test_compliance_schema.py]
tech_stack:
  added: []
  patterns: [compliance-builder-helper, phase-verified-date-constant]
key_files:
  modified:
    - quirk/compliance/__init__.py
decisions:
  - "D-05: _soc2() returns SOC2 CC 2017-rev builder dict with 5-key shape matching existing helpers"
  - "D-06: CC6.7 for transport/cipher/protocol findings; CC6.6 for auth and key/cert findings; both for mixed-domain"
  - "D-07: _iso() uses ISO 27001:2022 8.x clause numbering exclusively; A.x.x IDs rejected by unit test"
  - "D-08: 8.24 for algorithm/key-size findings; 8.26 for TLS/protocol transport"
  - "D-09: Full parity — all 24 COMPLIANCE_MAP keys carry SOC2 + ISO entries"
metrics:
  duration: "~10 minutes"
  completed: "2026-05-05"
  tasks_completed: 2
  files_modified: 1
---

# Phase 52 Plan 03: SOC2 + ISO 27001:2022 Compliance Helpers and Map Extension Summary

**One-liner:** SOC2 CC 2017-rev and ISO 27001:2022 8.x framework coverage added to all 24 COMPLIANCE_MAP keys via `_soc2()` and `_iso()` builder helpers following the existing `_pci/_hipaa/_fips` pattern.

## What Was Built

### Task 1: `_soc2`/`_iso` helpers and Phase 52 URL constants (commit d02885d)

Added to `quirk/compliance/__init__.py` immediately after the existing `_fips()` helper:

- `_PHASE_52_VERIFIED: str = "2026-05-05"` — phase-scoped freshness date constant
- `_SOC2_CC_URL` — AICPA Trust Services Criteria URL constant
- `_ISO_27001_URL` — ISO 27001:2022 official URL constant
- `_soc2(control: str)` — returns `{"framework": "SOC2 CC", "version": "2017-rev", ...}` 5-key dict
- `_iso(control: str)` — returns `{"framework": "ISO 27001:2022", "version": "ISO 27001:2022", ...}` 5-key dict

Both helpers follow the exact shape of `_pci/_hipaa/_fips`: no extra keys, no missing keys, no validation inside the helper.

### Task 2: COMPLIANCE_MAP extension with SOC2 + ISO entries (commit 90d567d)

Extended all 24 COMPLIANCE_MAP keys with `_soc2()` and `_iso()` calls per D-06/D-08/D-09:

**Transport/cipher/protocol findings (CC6.7 + ISO 8.26):** Plaintext HTTP, Legacy TLS cipher suites, STARTTLS downgrade, Weak/Non-PFS email cipher, Plaintext Kafka/AMQP, Weak broker cipher, End-of-life container image, Severely/Outdated Python cryptography/pyOpenSSL/libgcrypt container packages

**Auth/cert/key findings (CC6.6 + ISO 8.24):** TLS cert expired/expiring/self-signed/untrusted CA, Undersized RSA/ECDSA key, Quantum-vulnerable RSA/ECDSA key, Container image uses quantum-vulnerable crypto library

**Mixed-domain findings (CC6.6 + CC6.7 + ISO 8.26):** Legacy TLS versions allowed (TLS 1.0/1.1), Plaintext Redis listener (no auth)

Final counts: 24 keys; SOC2: 26 entries (2 mixed-domain keys carry two CC6.x entries each); ISO: 24 entries.

## Deviations from Plan

**Note — key count discrepancy (benign):** The plan and RESEARCH.md narrative text says "23 COMPLIANCE_MAP keys" but the actual source file has 24 keys. The RESEARCH.md coverage audit table has 24 rows — all 24 were extended. No coverage gap. The "23" in the plan text is a minor off-by-one in the narrative only; the table (the canonical source) is correct.

No other deviations — plan executed per spec.

## Test Results

All 8 tests in `tests/test_compliance_schema.py` GREEN:

- `test_module_imports` — PASS
- `test_every_entry_has_required_keys` — PASS (no regression)
- `test_last_verified_parses_as_iso_date` — PASS (no regression)
- `test_source_url_is_https` — PASS (no regression)
- `test_soc2_entries_present` — PASS (26 CC6.x control IDs; threshold >= 3)
- `test_iso_entries_present` — PASS (24 ISO 27001:2022 entries; threshold >= 3)
- `test_iso_rejects_legacy_control_ids` — PASS (zero A.x.x IDs)
- `test_iso_version_string_exact` — PASS (version = "ISO 27001:2022")

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes introduced. This plan modifies only the in-process compliance mapping dict — no new trust boundaries.

## Self-Check: PASSED

- [x] `quirk/compliance/__init__.py` exists and contains `def _soc2` and `def _iso`
- [x] Commit d02885d exists (Task 1 — helpers + constants)
- [x] Commit 90d567d exists (Task 2 — COMPLIANCE_MAP extension)
- [x] All 8 schema tests GREEN
- [x] Zero A.x.x ISO control IDs
- [x] D-09 parity verified: no COMPLIANCE_MAP key missing SOC2 or ISO entries
