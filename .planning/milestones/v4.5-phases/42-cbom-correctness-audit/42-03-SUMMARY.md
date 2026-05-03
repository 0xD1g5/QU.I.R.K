---
phase: 42-cbom-correctness-audit
plan: 03
subsystem: cbom
status: complete
tags: [cbom, golden-snapshot, fixtures, drift-control, profile-coverage]
requires: [42-01]
provides:
  - "tests/_cbom_profiles.py::PROFILE_ENDPOINTS (consumed by Plans 02 + 04)"
  - "16 per-profile CryptoEndpoint synthesizers (3 shape-golden + 13 lightweight)"
  - "3 shape-golden CBOM fixtures (pki, vault, saml)"
  - "tests/fixtures/cbom/CHANGELOG.md (D-09 drift rationale log)"
affects:
  - tests/test_cbom_motion_endpoints.py
  - tests/test_cbom_motion_golden.py
  - tests/_cbom_profiles.py
  - tests/fixtures/cbom/expected_pki_cbom.json
  - tests/fixtures/cbom/expected_vault_cbom.json
  - tests/fixtures/cbom/expected_saml_cbom.json
  - tests/fixtures/cbom/CHANGELOG.md
tech-stack:
  added: []
  patterns: ["snapshot-golden", "single-source-of-truth registry", "Phase 35 regen-then-verify"]
key-files:
  created:
    - tests/_cbom_profiles.py
    - tests/fixtures/cbom/expected_pki_cbom.json
    - tests/fixtures/cbom/expected_vault_cbom.json
    - tests/fixtures/cbom/expected_saml_cbom.json
    - tests/fixtures/cbom/CHANGELOG.md
  modified:
    - tests/test_cbom_motion_endpoints.py (+361 lines, 16 new synthesizers)
    - tests/test_cbom_motion_golden.py (+45 lines, 3 new snapshot tests + regen tuple)
decisions:
  - "Defaulted DAR-skip and identity profiles to RSA/2048 cert_pubkey_alg so Pass 1 always emits a known algorithm component"
  - "Used real weak-algo observables (RSASHA1, RC4-HMAC, ssh-dss, MD5) for dnssec/kerberos/ssh-weak/source profiles to surface UNKNOWNs for Plan 04 gap-fill"
  - "REGEN command requires `-m \"\"` to override the project default `addopts = \"-m 'not slow'\"` — documented in CHANGELOG.md"
metrics:
  duration_minutes: 8
  completed_at: 2026-04-30
  tasks_total: 3
  tasks_completed: 3
  files_created: 5
  files_modified: 2
---

# Phase 42 Plan 03: CBOM Shape Goldens + Profile Coverage + Shared Profile Map Summary

One-liner: 16 per-profile CBOM endpoint synthesizers + 3 shape-golden fixtures + a shared
`tests/_cbom_profiles.py` registry that Plans 02 and 04 both import — the profile→synthesizer
map is no longer duplicated and every shipped chaos lab profile (18 total) now has at least
one representative endpoint for downstream validation.

## What Was Built

### Task 1 — 16 endpoint synthesizers in `tests/test_cbom_motion_endpoints.py` (commit `0033f93`)

**3 shape-golden synthesizers** (rich; consumed by Task 2's snapshot tests):

| Synthesizer | Profile | Shape | Source / Port |
| --- | --- | --- | --- |
| `_build_pki_lab_endpoints` | pki | TLS-with-cert | mtls-stepca-gateway, port 17443 |
| `_build_vault_lab_endpoints` | vault | DAR (Pass-1-only) | HashiCorp Vault, port 28200 |
| `_build_saml_lab_endpoints` | saml | Identity (no TLS) | simplesamlphp IdP, port 8080 |

**13 lightweight synthesizers** (1–3 endpoints each; sourced from `expected_results_v3.md`):

| Synthesizer | Profile | Algo observables |
| --- | --- | --- |
| `_build_cloud_lab_endpoints` | cloud | RSA/2048, TLS_ECDHE_RSA_… |
| `_build_database_lab_endpoints` | database | RSA/2048 (Pass-1 only — DAR_SKIP) |
| `_build_dnssec_lab_endpoints` | dnssec | **RSASHA1** (likely UNKNOWN — Plan 04) |
| `_build_identity_lab_endpoints` | identity | RSA/2048, TLS_ECDHE_RSA_… |
| `_build_jwt_lab_endpoints` | jwt | RSA/2048 (RS256) |
| `_build_kerberos_lab_endpoints` | kerberos | **RC4-HMAC** (likely UNKNOWN — Plan 04) |
| `_build_ldaps_lab_endpoints` | ldaps | RSA/2048, TLS_ECDHE_RSA_… |
| `_build_phaseA_lab_endpoints` | phaseA | RSA/2048 + RSA/1024 + sha1WithRSAEncryption |
| `_build_registry_lab_endpoints` | registry | RSA/2048 |
| `_build_source_lab_endpoints` | source | **MD5** |
| `_build_ssh_weak_lab_endpoints` | ssh-weak | **ssh-dss** (likely UNKNOWN — Plan 04) |
| `_build_storage_lab_endpoints` | storage | AES-256, RSA/2048 |
| `_build_storage_s3_lab_endpoints` | storage-s3 | AES-256 (MinIO) |

Total: 16 synthesizers, 21 endpoints across 13 lightweight functions + 5 across the 3 shape-golden functions.

### Task 2 — Goldens, snapshot tests, CHANGELOG (commit `5c3ab2e`)

- 3 new snapshot tests in `tests/test_cbom_motion_golden.py`:
  - `test_pki_cbom_matches_snapshot`
  - `test_vault_cbom_matches_snapshot`
  - `test_saml_cbom_matches_snapshot`
- 3 new fixture files (byte sizes from `stat -f %z`):
  - `expected_pki_cbom.json` — 2130 bytes
  - `expected_vault_cbom.json` — 272 bytes (algorithm-only — VAULT in DAR_SKIP_PROTOCOLS)
  - `expected_saml_cbom.json` — 262 bytes (algorithm-only — SAML has no TLS shape)
- `tests/fixtures/cbom/CHANGELOG.md` created with Phase 42 entry per D-09
- `test_generate_fixtures` extended from 2 entries to 5 entries
- Existing `expected_email_cbom.json` and `expected_broker_cbom.json` byte-identical (verified via `git diff` — empty diff after regen)

### Task 3 — `tests/_cbom_profiles.py` (commit `ee057f8`)

`PROFILE_ENDPOINTS` is the single source of truth, exposing all 18 chaos lab profiles:

```
broker, cloud, database, dnssec, email, identity, jwt, kerberos, ldaps,
phaseA, pki, registry, saml, source, ssh-weak, storage, storage-s3, vault
```

- `from tests._cbom_profiles import PROFILE_ENDPOINTS` succeeds
- `len(PROFILE_ENDPOINTS) == 18` (verified by import-time assert)
- Every value is a callable returning a non-empty `list[CryptoEndpoint]`
- Plans 02 + 04 will both `from tests._cbom_profiles import PROFILE_ENDPOINTS` — no duplicate registry

## Verification

```bash
$ .venv/bin/python -m pytest tests/test_cbom_motion_endpoints.py tests/test_cbom_motion_golden.py tests/test_cbom_builder.py -x -q
............................................................             [100%]
60 passed, 1 deselected in 0.13s
```

```bash
$ .venv/bin/python -m pytest tests/test_cbom_motion_golden.py -x -v
test_email_cbom_matches_snapshot  PASSED
test_broker_cbom_matches_snapshot PASSED
test_pki_cbom_matches_snapshot    PASSED
test_vault_cbom_matches_snapshot  PASSED
test_saml_cbom_matches_snapshot   PASSED
+ 6 structural-invariant tests PASSED
```

```bash
$ .venv/bin/python -c "from tests._cbom_profiles import PROFILE_ENDPOINTS; assert len(PROFILE_ENDPOINTS) == 18"
# OK — all 18 profiles, all callable, all non-empty
```

## CHANGELOG.md Entry (verbatim)

```markdown
## 2026-04-30 — Phase 42: shape-coverage expansion

**Reason:** Added three goldens to cover the curated CBOM output shapes
per D-07 (Phase 42 — CBOM Correctness Audit):

- `expected_pki_cbom.json` — TLS-with-cert shape (mTLS step-CA, port 17443)
- `expected_vault_cbom.json` — Data-at-rest shape (VAULT protocol; Pass 2/3 skipped, Pass 1 emits algorithm components only)
- `expected_saml_cbom.json` — Identity shape (SAML IdP signing cert; no TLS protocol component)

**Files touched:** new files only — no diff in `expected_email_cbom.json` or `expected_broker_cbom.json`.

**Regen:** `REGEN_CBOM_FIXTURES=1 pytest tests/test_cbom_motion_golden.py::test_generate_fixtures -s -m ""`
```

## Likely UNKNOWN-Classification Gaps for Plan 04

The lightweight synthesizers intentionally include weak-algo observables that may not be in
the classifier's `_ALGORITHM_TABLE`. Plan 04 should verify and add table rows for:

- **`RSASHA1`** (dnssec — DNSSEC RFC4034 algo 5)
- **`RC4-HMAC`** (kerberos — RFC 4757 enctype 23)
- **`ssh-dss`** (ssh-weak — SSH hostkey algorithm)

`MD5` (source profile) is already in `_ALGORITHM_TABLE` and should classify cleanly. `RSA`,
`AES-256`, `RSA-2048` are all known.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] REGEN command requires `-m ""` to override pytest config**

- **Found during:** Task 2 — initial `REGEN_CBOM_FIXTURES=1 pytest …::test_generate_fixtures -s` collected 1 item but immediately deselected it.
- **Issue:** `pyproject.toml` sets `addopts = "-m 'not slow'"` and `test_generate_fixtures` is decorated with `@pytest.mark.slow`, so the slow-deselect filter blocks regeneration even when `REGEN_CBOM_FIXTURES=1` is set.
- **Fix:** Used `-m ""` to clear the marker filter for the regen invocation. Documented in `tests/fixtures/cbom/CHANGELOG.md`. The plan's verbatim regen command was missing this flag — propagating the corrected form.
- **Files modified:** `tests/fixtures/cbom/CHANGELOG.md` (regen line)
- **Commit:** `5c3ab2e`

No other deviations. Existing email/broker goldens byte-identical, all acceptance criteria met.

## Self-Check: PASSED

- `tests/test_cbom_motion_endpoints.py` — FOUND (361 new lines, 16 synthesizers)
- `tests/test_cbom_motion_golden.py` — FOUND (3 new snapshot tests + regen tuple extended)
- `tests/_cbom_profiles.py` — FOUND
- `tests/fixtures/cbom/expected_pki_cbom.json` — FOUND (2130 bytes)
- `tests/fixtures/cbom/expected_vault_cbom.json` — FOUND (272 bytes)
- `tests/fixtures/cbom/expected_saml_cbom.json` — FOUND (262 bytes)
- `tests/fixtures/cbom/CHANGELOG.md` — FOUND, contains "Phase 42"
- Commits `0033f93`, `5c3ab2e`, `ee057f8` — FOUND in `git log`
- Existing `expected_email_cbom.json` / `expected_broker_cbom.json` — UNCHANGED (verified `git diff` empty after regen)
