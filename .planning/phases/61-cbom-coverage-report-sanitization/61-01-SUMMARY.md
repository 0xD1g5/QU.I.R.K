---
phase: 61
plan: 01
subsystem: cbom-builder
tags: [cbom, audit, cr-01, cr-02, pass-1, coverage, testing]
one_liner: "CBOM Pass-1 now registers algorithm components for all 14 protocol families; VAULT gets dedicated elif branch; locked with parametrized coverage test and golden snapshot"
dependency_graph:
  requires: []
  provides:
    - quirk/cbom/builder.py Pass-1 branches for VAULT, CONTAINER, MYSQL, POSTGRESQL/RDS, S3/AZURE_BLOB, MOTION_PLAINTEXT guard, SSH host-key fallback, SOURCE raw-rule-ID fallback
    - tests/test_cbom_coverage.py parametrized per-family coverage gate (14 families)
    - tests/test_cbom_vault_consistency.py + cbom_vault_golden.json golden snapshot
  affects:
    - CBOM artifact completeness for clients (VAULT, DB, Container, Source, SSH-weak, Storage families now emit algorithm components)
tech_stack:
  added: []
  patterns:
    - "elif ep.protocol == 'X': pattern for each Pass-1 family branch"
    - "pytest.param(..., id='family-name') for named parametrized regression guards"
    - "sorted (name, str(type)) tuple snapshot for non-deterministic UUID-stable golden fixture"
key_files:
  created:
    - tests/test_cbom_coverage.py
    - tests/test_cbom_vault_consistency.py
    - tests/fixtures/cbom/cbom_vault_golden.json
  modified:
    - quirk/cbom/builder.py
    - tests/fixtures/cbom/expected_vault_cbom.json
decisions:
  - "D-01: VAULT gets dedicated elif branch in Pass-1 (mirrors SAML/KERBEROS pattern); stays in DAR_SKIP_PROTOCOLS for Pass-2/3"
  - "D-02: Golden snapshot uses sorted (name, str(type)) tuples to avoid UUID/serialNumber non-determinism"
  - "D-03: CONTAINER cipher_suite (library name) is the algorithm component name"
  - "D-04: MYSQL parses service_detail 'MySQL/<cipher>-ok|weak'; POSTGRESQL/RDS use cert_pubkey_alg"
  - "D-05: S3/AZURE_BLOB map to AES-256 when not 'unencrypted'"
  - "D-06: SOURCE raw rule ID fallback when hint map returns None"
  - "D-07: SSH host-key fallback adds cert_pubkey_alg at end of SSH block (deduped by bom_ref)"
  - "D-08: Explicit MOTION_PLAINTEXT_PROTOCOLS guard before TLS else (prevents plaintext brokers from hitting TLS branch)"
metrics:
  duration: "~15 minutes"
  completed: "2026-05-10"
  tasks_completed: 3
  tasks_total: 3
  files_modified: 5
---

# Phase 61 Plan 01: CBOM Pass-1 Coverage + VAULT Golden Snapshot Summary

## What Was Built

### Task 1: Pass-1 Builder Branches for Zero-Algo Families

Modified `quirk/cbom/builder.py` to add/correct 9 Pass-1 dispatch chain changes:

1. **CONTAINER** — changed from `pass` to register `ep.cipher_suite` (library name like "openssl")
2. **SOURCE** — added raw rule ID fallback: `algo_to_register = algo_hint or ep.cipher_suite`
3. **VAULT** — new dedicated `elif ep.protocol == "VAULT":` branch registering `cert_pubkey_alg` with `key_size=cert_pubkey_size`. VAULT stays in DAR_SKIP_PROTOCOLS for Pass-2/3.
4. **MYSQL** — new branch parsing `service_detail` as `"MySQL/<cipher>-ok|weak"`, sentinel-filtering `SSL-OFF` and `UNSPECIFIED`
5. **POSTGRESQL/RDS** — new branch registering `cert_pubkey_alg` when set
6. **S3/AZURE_BLOB** — new branch emitting `"AES-256"` for all non-unencrypted postures
7. **KUBERNETES** — isolated to its own `pass` elif (previously bundled with DB/storage)
8. **MOTION_PLAINTEXT_PROTOCOLS** — explicit guard before TLS else (prevents KAFKA-PLAIN/AMQP-PLAIN/REDIS-PLAIN from hitting TLS branch)
9. **SSH host-key fallback** (D-07) — `cert_pubkey_alg` registered at end of SSH block for ssh-weak endpoints with empty ssh_audit_json

Also regenerated `tests/fixtures/cbom/expected_vault_cbom.json` — VAULT endpoints previously fell to TLS else branch (producing "RSA-2048" by concatenation); now the dedicated VAULT branch produces "RSA" for `cert_pubkey_alg="RSA"`. This is an intentional fixture update.

### Task 2: Parametrized Per-Family Coverage Test (CBOM-COVER-01)

Created `tests/test_cbom_coverage.py` with:
- `_make_endpoint(**overrides)` factory (avoids 14-field constructors per family)
- 14 `pytest.param` cases with named IDs: `database-mysql`, `database-postgres`, `database-rds`, `container`, `source`, `ssh-weak`, `storage-s3`, `storage-azure`, `kafka-tls`, `email-starttls`, `vault`, `dnssec`, `saml`, `kerberos`
- Each asserts `len(algo_components) >= 1` — failure identifies the family by ID in CI output

All 14 cases pass.

### Task 3: VAULT Golden Snapshot Test + Fixture (CBOM-COVER-02)

Created `tests/test_cbom_vault_consistency.py` and `tests/fixtures/cbom/cbom_vault_golden.json`:
- 3 deterministic VAULT endpoints: `rsa-2048/2048`, `aes256-gcm96/256`, `ed25519/None`
- Snapshot key: `sorted([c.name, str(c.type)] for c in bom.components)` — stable across UUID/serialNumber churn
- `REGEN_CBOM_FIXTURES=1` env var gates regeneration
- Re-runs without env var pass on both runs (stable)
- Does NOT modify `expected_vault_cbom.json` (Phase 35 fixture)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Regenerated expected_vault_cbom.json golden fixture**
- **Found during:** Task 1 verification
- **Issue:** The existing `test_vault_cbom_matches_snapshot` in `test_cbom_motion_golden.py` expected `"RSA-2048"` (output of TLS else branch which concatenates alg+size). After adding the dedicated VAULT branch, VAULT endpoints with `cert_pubkey_alg="RSA"` now emit `"RSA"` (no size concatenation since the VAULT branch calls `_register_algorithm(ep.cert_pubkey_alg, ...)` directly). This is the correct behavior per D-01.
- **Fix:** Regenerated all golden fixtures via `REGEN_CBOM_FIXTURES=1 pytest tests/test_cbom_motion_golden.py::test_generate_fixtures -m slow`
- **Files modified:** `tests/fixtures/cbom/expected_vault_cbom.json`
- **Commit:** 0feedcd (included in Task 1 commit)

## Pre-existing Test Failures (Out of Scope)

Two pre-existing test failure categories confirmed unrelated to this plan's changes:

1. **`test_cbom_schema_validation.py`** — All failures due to missing `cyclonedx-python-lib[json-validation]` optional dependency (`MissingOptionalDependencyException`). Present before and after plan changes.

2. **`test_cbom_classifier_coverage.py::test_no_unknown_classifications_across_lab_profiles`** — Fails because `ssh-dss` is classified as `UNKNOWN` in the ssh-weak lab profile. Noted in codebase: "Plan 04 closes" (`tests/test_cbom_motion_endpoints.py:612`). Pre-existing.

Both logged to deferred-items for Phase 61 Plan 04.

## Known Stubs

None — all protocol families produce real algorithm components.

## Threat Flags

No new network endpoints, auth paths, or schema changes at trust boundaries introduced. All changes are pure Python builder logic and test fixtures.

## Self-Check: PASSED

Files exist:
- quirk/cbom/builder.py: FOUND
- tests/test_cbom_coverage.py: FOUND
- tests/test_cbom_vault_consistency.py: FOUND
- tests/fixtures/cbom/cbom_vault_golden.json: FOUND
- tests/fixtures/cbom/expected_vault_cbom.json: FOUND (regenerated)

Commits:
- 0feedcd: feat(61-01): add Pass-1 branches for zero-algo CBOM families
- 1b7c342: test(61-01): add parametrized per-family CBOM coverage test (CBOM-COVER-01)
- bf78d42: test(61-01): add VAULT CBOM golden snapshot test + fixture (CBOM-COVER-02)

All 71 targeted tests pass (71 passed, 1 skipped [REGEN gate], 1 deselected [slow mark]).
