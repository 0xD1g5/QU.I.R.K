---
phase: 42-cbom-correctness-audit
plan: 04
subsystem: cbom
status: complete
tags: [cbom, classifier, coverage-gate, nist-pqc]
requires: [42-01, 42-03]
provides:
  - "tests/test_cbom_classifier_coverage.py::test_no_unknown_classifications_across_lab_profiles (CBOM-02 gate)"
  - "tests/test_cbom_classifier_coverage.py::test_regenerate_coverage_report (REGEN_CBOM_COVERAGE=1)"
  - "docs/cbom-classifier-coverage.md (D-05 generated coverage report)"
  - "12 new _ALGORITHM_TABLE rows closing the Plan 03-surfaced gaps"
affects:
  - tests/test_cbom_classifier_coverage.py
  - docs/cbom-classifier-coverage.md
  - quirk/cbom/classifier.py
  - pyproject.toml
tech-stack:
  added: []
  patterns: ["pytest gate over registry × profile matrix", "regen-via-env-var (REGEN_CBOM_COVERAGE=1)", "single-source-of-truth registry import"]
key-files:
  created:
    - tests/test_cbom_classifier_coverage.py
    - docs/cbom-classifier-coverage.md
  modified:
    - quirk/cbom/classifier.py (+9 net lines, all inside _ALGORITHM_TABLE)
    - pyproject.toml (+1 line, pythonpath = ["."])
decisions:
  - "AES-256 (bare key-spec from storage profile) classified as BLOCK_CIPHER level 1 — matches the project's existing aes-256-gcm/ccm convention rather than aes-256-cbc's level 3"
  - "Added neighbour-size rows (rsa-3072/4096, aes-128/192, sha384/512withRSAEncryption, ecdsa-with-sha384/512) so the table reflects whole RFC families rather than chasing future single-name gaps"
  - "Rule 3 auto-fix: added `pythonpath = [\".\"]` to [tool.pytest.ini_options]; without this (or Plan 02's tests/__init__.py) pytest cannot resolve `from tests._cbom_profiles import …`"
metrics:
  duration_minutes: 12
  completed_at: 2026-04-30
  tasks_total: 2
  tasks_completed: 2
  files_created: 2
  files_modified: 2
---

# Phase 42 Plan 04: CBOM Classifier Coverage Gate + Gap-Fill Summary

One-liner: Pytest gate that walks every algorithm component emitted by `build_cbom()` for all 18
chaos lab profiles asserting zero `UNKNOWN` classifications, plus a deterministic regen-mode
generator producing `docs/cbom-classifier-coverage.md` and 12 new `_ALGORITHM_TABLE` rows that
closed five gate-surfaced gaps (RSA-1024/2048, AES-256, sha1/sha256-with-RSA-Encryption).

## What Was Built

### Task 1 — Coverage gate + regen report (commit `806dc52`)

Created `tests/test_cbom_classifier_coverage.py` with two tests:

- **`test_no_unknown_classifications_across_lab_profiles`** — walks
  `bom.components` for every profile in `tests._cbom_profiles.PROFILE_ENDPOINTS`,
  filters by `crypto_properties.asset_type.value == "algorithm"`, calls
  `classify_algorithm(c.name)`, and asserts no UNKNOWN result for any name
  except the JWT `alg:none` sentinel (Pitfall #4).
- **`test_regenerate_coverage_report`** — gated by `REGEN_CBOM_COVERAGE=1`
  and `@pytest.mark.slow`. Writes `docs/cbom-classifier-coverage.md` with a
  Markdown table of `Algorithm Name | Primitive | NIST Level | Classical Bits |
  Surfaced By Profiles`, sorted by name → byte-identical on repeat runs.

The gate imports `PROFILE_ENDPOINTS` from `tests._cbom_profiles` exactly the
same way Plan 02's schema-validation harness does — single source of truth, no
local copy (M4 satisfied).

### Task 2 — Gap-fill in `_ALGORITHM_TABLE` (commit `9d59a5b`)

Initial gate run flagged five UNKNOWN classifications:

| Name | Profiles | Resolved To |
|------|----------|-------------|
| `AES-256` | storage | `BLOCK_CIPHER, level 1, 256` |
| `RSA-1024` | phaseA | `PKE, level 0, 80` |
| `RSA-2048` | broker, cloud, email, identity, ldaps, phaseA, pki, vault | `PKE, level 0, 112` |
| `sha1WithRSAEncryption` | phaseA | `SIGNATURE, level 0, 80` |
| `sha256WithRSAEncryption` | broker, cloud, email, identity, ldaps, phaseA, pki | `SIGNATURE, level 0, 112` |

Diff snippet (additions only — `_FALLBACK` and `classify_algorithm()` body untouched):

```python
# CycloneDX canonical names section
"rsa": (CryptoPrimitive.PKE, 0, 112),
"rsa-1024": (CryptoPrimitive.PKE, 0, 80),     # NEW
"rsa-2048": (CryptoPrimitive.PKE, 0, 112),    # NEW
"rsa-3072": (CryptoPrimitive.PKE, 0, 128),    # NEW (neighbour)
"rsa-4096": (CryptoPrimitive.PKE, 0, 152),    # NEW (neighbour)
...
"aes-128": (CryptoPrimitive.BLOCK_CIPHER, 1, 128),  # NEW (neighbour)
"aes-192": (CryptoPrimitive.BLOCK_CIPHER, 1, 192),  # NEW (neighbour)
"aes-256": (CryptoPrimitive.BLOCK_CIPHER, 1, 256),  # NEW

# New X.509 cert signature OIDs section
"md5withrsaencryption":    (CryptoPrimitive.SIGNATURE, 0, 64),   # NEW (neighbour)
"sha1withrsaencryption":   (CryptoPrimitive.SIGNATURE, 0, 80),   # NEW
"sha256withrsaencryption": (CryptoPrimitive.SIGNATURE, 0, 112),  # NEW
"sha384withrsaencryption": (CryptoPrimitive.SIGNATURE, 0, 112),  # NEW (neighbour)
"sha512withrsaencryption": (CryptoPrimitive.SIGNATURE, 0, 112),  # NEW (neighbour)
"ecdsa-with-sha256":       (CryptoPrimitive.SIGNATURE, 0, 128),  # NEW (neighbour)
"ecdsa-with-sha384":       (CryptoPrimitive.SIGNATURE, 0, 192),  # NEW (neighbour)
"ecdsa-with-sha512":       (CryptoPrimitive.SIGNATURE, 0, 256),  # NEW (neighbour)
```

After re-running the regen, the report shows zero `UNKNOWN` rows in the Primitive
column. Determinism verified: a second consecutive regen run produces a
byte-identical file (`diff` exit 0).

## Coverage Surface

15 distinct algorithm names surfaced by the 18-profile harness:

| Name | Primitive | NIST | Classical | Profiles |
|------|-----------|------|-----------|----------|
| AES-128-CBC | BLOCK_CIPHER | 1 | 128 | broker |
| AES-256 | BLOCK_CIPHER | 1 | 256 | storage |
| AES-256-GCM | AE | 1 | 256 | cloud, identity, ldaps, phaseA, pki |
| ChaCha20-Poly1305 | AE | 1 | 256 | email |
| RC4-HMAC | BLOCK_CIPHER | 0 | 128 | kerberos |
| RSA | PKE | 0 | 112 | broker, cloud, email, identity, jwt, ldaps, phaseA, pki, saml |
| RSA-1024 | PKE | 0 | 80 | phaseA |
| RSA-2048 | PKE | 0 | 112 | broker, cloud, email, identity, ldaps, phaseA, pki, vault |
| RSASHA1 | PKE | — | — | dnssec |
| SHA-1 | HASH | 0 | 80 | broker |
| SHA-256 | HASH | 0 | 128 | email |
| SHA-384 | HASH | 2 | 192 | cloud, email, identity, ldaps, phaseA, pki |
| X25519 | KEY_AGREE | 0 | 128 | cloud, identity, ldaps, phaseA, pki |
| sha1WithRSAEncryption | SIGNATURE | 0 | 80 | phaseA |
| sha256WithRSAEncryption | SIGNATURE | 0 | 112 | broker, cloud, email, identity, ldaps, phaseA, pki |

10 surfaced names were already classified pre-Plan-04; 5 needed new rows
(closed by Task 2 along with 7 forward-looking neighbour rows).

## Out-of-Scope Observations

The following profiles emitted **zero** algorithm components from `build_cbom()`:
`database, registry, source, ssh-weak, storage-s3`. This is a Plan 03 / builder
filtering concern (DAR_SKIP profiles or empty algo decompositions) — out of
scope for Plan 04, which only gates what `build_cbom` actually surfaces. Their
absence does not cause a gate failure; it just means those profiles do not
contribute names to the coverage report. If Phase 42 (or a follow-on) needs
non-empty algo coverage for them, that's a Plan 03 / builder task, not a
classifier task. Logged for transparency, no action taken.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] Added `pythonpath = ["."]` to `[tool.pytest.ini_options]`**
- **Found during:** Task 1 first pytest invocation
- **Issue:** `from tests._cbom_profiles import PROFILE_ENDPOINTS` (the M4-mandated
  import) failed at pytest collection time with `ModuleNotFoundError: No module
  named 'tests._cbom_profiles'`. Pytest's rootdir-importer mode (no `conftest`-set
  pythonpath) does not put the project root on `sys.path`, so the `tests` namespace
  package is not resolvable from within a collected test file.
- **Fix:** Added `pythonpath = ["."]` to the existing `[tool.pytest.ini_options]`
  block in `pyproject.toml`. (Plan 02 separately added `tests/__init__.py` for the
  same root cause — both fixes are valid; either alone would suffice. Leaving both
  in place provides defence-in-depth and matches the convention other Python
  projects use.)
- **Files modified:** `pyproject.toml` (+1 line)
- **Commit:** `806dc52`

### Other Deviations

None — plan executed exactly as written aside from the Rule 3 fix above.

## Verification Checklist

- [x] `pytest tests/test_cbom_classifier_coverage.py -x` exits 0 (1 passed, 1 slow-deselected)
- [x] `pytest tests/ -k cbom -x` exits 0 (141 passed, 587 deselected)
- [x] `python -m compileall quirk/cbom/classifier.py` exits 0
- [x] `docs/cbom-classifier-coverage.md` exists with the `# CBOM Classifier Coverage Report` header and `| Algorithm Name |` table
- [x] Gate test contains `from tests._cbom_profiles import PROFILE_ENDPOINTS` (M4)
- [x] Gate test does NOT define a local `PROFILE_ENDPOINTS = {`  copy
- [x] Pitfall #4 honored: `name.lower() != "none"` exclusion present
- [x] Determinism: second consecutive regen produces zero git diff
- [x] `_ALGORITHM_TABLE` additions only — no edits to `_FALLBACK` or `classify_algorithm()` body

## Commits

| Hash | Message |
|------|---------|
| `806dc52` | `test(42-04): add CBOM classifier coverage gate + regen report` |
| `9d59a5b` | `feat(42-04): close classifier coverage gaps for 18-profile gate` |

## Self-Check: PASSED

- `tests/test_cbom_classifier_coverage.py` — present (commit `806dc52`)
- `docs/cbom-classifier-coverage.md` — present, 24 lines, deterministic (commits `806dc52`, `9d59a5b`)
- `quirk/cbom/classifier.py` — 12 new `_ALGORITHM_TABLE` rows (commit `9d59a5b`)
- `pyproject.toml` — `pythonpath = ["."]` added (commit `806dc52`)
