---
phase: 42-cbom-correctness-audit
plan: 02
subsystem: cbom
tags: [cbom, cyclonedx, schema-validation, pytest]
requires: [42-01, 42-03]
provides: [CBOM-01-schema-validation-gate]
affects: [tests/test_cbom_schema_validation.py, tests/__init__.py]
tech-stack:
  added: [yaml.safe_load (PyYAML 6.0.3 transitive dep), JsonStrictValidator, XmlValidator]
  patterns: [pytest.mark.parametrize over PROFILE_ENDPOINTS, drift-sentinel via yaml.safe_load, validate_str(...) is None]
key-files:
  created:
    - tests/test_cbom_schema_validation.py
    - tests/__init__.py
  modified: []
decisions:
  - "Imported PROFILE_ENDPOINTS from tests/_cbom_profiles.py (Plan 03) — zero duplication of profile→synthesizer map"
  - "Used yaml.safe_load (not regex) for compose file parsing per Pitfall warning; PyYAML 6.0.3 already transitively present"
  - "Asserted validate_str(...) is None instead of try/except per RESEARCH Pitfall #2 (cyclonedx-python-lib returns errors, does not raise)"
metrics:
  duration: ~10min
  completed: 2026-04-30
---

# Phase 42 Plan 02: CycloneDX 1.6 schema validation harness Summary

CBOM-01 schema validation gate landed: every shipped chaos lab profile now produces a CycloneDX 1.6 spec-valid JSON and XML CBOM, with a yaml-based drift sentinel locking the parametrize set to docker-compose.yml.

## What Was Built

`tests/test_cbom_schema_validation.py` (92 lines) with two tests:

1. **`test_cbom_validates_against_cyclonedx_1_6`** — parametrized over 18 chaos lab profiles imported from `tests/_cbom_profiles.PROFILE_ENDPOINTS`. For each profile, calls `build_cbom(synthesizer())` + `write_cbom_files(bom, tmp_path, "test")`, then asserts both `JsonStrictValidator(SchemaVersion.V1_6).validate_str(...) is None` and `XmlValidator(SchemaVersion.V1_6).validate_str(...) is None`.

2. **`test_parametrize_set_matches_docker_compose_profiles`** — drift sentinel that parses `quantum-chaos-enterprise-lab/docker-compose.yml` via `yaml.safe_load`, walks every service's `.profiles` list, and asserts the union equals `PROFILE_ENDPOINTS.keys()`. Includes defensive guard `assert len(profiles) >= 18` to catch parser regressions if YAML structure changes.

### Profile Inventory Verified (18 profiles)

```
broker, cloud, database, dnssec, email, identity, jwt, kerberos, ldaps,
phaseA, pki, registry, saml, source, ssh-weak, storage, storage-s3, vault
```

Drift sentinel confirms `PROFILE_ENDPOINTS.keys()` ≡ `_profiles_from_compose()`.

### pytest Output

```
tests/test_cbom_schema_validation.py::test_cbom_validates_against_cyclonedx_1_6[broker]     PASSED
tests/test_cbom_schema_validation.py::test_cbom_validates_against_cyclonedx_1_6[cloud]      PASSED
tests/test_cbom_schema_validation.py::test_cbom_validates_against_cyclonedx_1_6[database]   PASSED
tests/test_cbom_schema_validation.py::test_cbom_validates_against_cyclonedx_1_6[dnssec]     PASSED
tests/test_cbom_schema_validation.py::test_cbom_validates_against_cyclonedx_1_6[email]      PASSED
tests/test_cbom_schema_validation.py::test_cbom_validates_against_cyclonedx_1_6[identity]   PASSED
tests/test_cbom_schema_validation.py::test_cbom_validates_against_cyclonedx_1_6[jwt]        PASSED
tests/test_cbom_schema_validation.py::test_cbom_validates_against_cyclonedx_1_6[kerberos]   PASSED
tests/test_cbom_schema_validation.py::test_cbom_validates_against_cyclonedx_1_6[ldaps]      PASSED
tests/test_cbom_schema_validation.py::test_cbom_validates_against_cyclonedx_1_6[phaseA]     PASSED
tests/test_cbom_schema_validation.py::test_cbom_validates_against_cyclonedx_1_6[pki]        PASSED
tests/test_cbom_schema_validation.py::test_cbom_validates_against_cyclonedx_1_6[registry]   PASSED
tests/test_cbom_schema_validation.py::test_cbom_validates_against_cyclonedx_1_6[saml]       PASSED
tests/test_cbom_schema_validation.py::test_cbom_validates_against_cyclonedx_1_6[source]     PASSED
tests/test_cbom_schema_validation.py::test_cbom_validates_against_cyclonedx_1_6[ssh-weak]   PASSED
tests/test_cbom_schema_validation.py::test_cbom_validates_against_cyclonedx_1_6[storage]    PASSED
tests/test_cbom_schema_validation.py::test_cbom_validates_against_cyclonedx_1_6[storage-s3] PASSED
tests/test_cbom_schema_validation.py::test_cbom_validates_against_cyclonedx_1_6[vault]      PASSED
tests/test_cbom_schema_validation.py::test_parametrize_set_matches_docker_compose_profiles  PASSED

============================== 19 passed in 0.63s ==============================
```

Zero JSON/XML schema violations across all 18 profiles → D-03 zero-violation bar met.

### PyYAML Dependency

`pip show pyyaml` returned **PyYAML 6.0.3** — transitive dep via cyclonedx-python-lib. No `pyproject.toml` change needed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocker] Added `tests/__init__.py` to make `tests` a real package**

- **Found during:** Task 1 — pytest collection
- **Issue:** Plan 42-03 introduced cross-test imports (`from tests.test_cbom_motion_endpoints import ...`, `from tests._cbom_profiles import ...`) but `tests/` had no `__init__.py`. Under pytest's rootdir-prepend import mode, the `tests` namespace was not importable, so collection of `test_cbom_motion_golden.py`, `test_cbom_classifier_coverage.py`, `test_skip_registry.py`, and (now) `test_cbom_schema_validation.py` failed with `ModuleNotFoundError: No module named 'tests.X'`.
- **Verified pre-existing:** confirmed via `git stash` + collect — 4 collection errors at HEAD before any 42-02 work began. Plan 42-03 introduced the regression by adding the import pattern without making the package importable.
- **Fix:** Created empty `tests/__init__.py` so pytest uses package-mode imports.
- **Files modified:** `tests/__init__.py` (new, empty)
- **Commit:** `6e0afad fix(42-02): add tests/__init__.py to make tests a real package`
- **Verification:** `pytest tests/ --collect-only` now collects 717/728 tests with zero import errors (was 685/694 with 4 errors).

## Acceptance Criteria

| Check | Result |
|-------|--------|
| File exists | ✓ |
| `from tests._cbom_profiles import PROFILE_ENDPOINTS` count | 1 |
| `import yaml` count | 1 |
| `JsonStrictValidator(SchemaVersion.V1_6)` count | 1 |
| `XmlValidator(SchemaVersion.V1_6)` count | 1 |
| `is None` count | 3 (≥2 required) |
| try/except wrap of validate_str | 0 |
| `len(profiles) >= 18` guard | 1 |
| Parametrize generates exactly 18 cases | ✓ |
| `test_cbom_validates_against_cyclonedx_1_6` exits 0 | ✓ |
| `test_parametrize_set_matches_docker_compose_profiles` exits 0 | ✓ |

## Threat Model Outcomes

| Threat ID | Status |
|-----------|--------|
| T-42-01 (Repudiation: malformed CBOM rejected by customer CI) | Mitigated — per-profile JSON+XML validator gate, zero violations |
| T-42-04 (Tampering: silent coverage drift) | Mitigated — yaml.safe_load drift sentinel locked to docker-compose.yml |
| T-42-10 (Tampering: silent regex parser bug) | Mitigated — defensive `assert len(profiles) >= 18` in `_profiles_from_compose` |

## Self-Check: PASSED

- `tests/test_cbom_schema_validation.py` exists ✓
- `tests/__init__.py` exists ✓
- Commit `6e0afad` (init.py) found ✓
- Commit `5926fa7` (schema validation harness) found ✓
- `pytest tests/test_cbom_schema_validation.py` 19 passed ✓
