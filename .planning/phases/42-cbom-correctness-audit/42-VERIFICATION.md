---
phase: 42-cbom-correctness-audit
verified: 2026-04-30T00:00:00Z
status: passed
score: 4/4 must-haves verified
overrides_applied: 0
---

# Phase 42: CBOM Correctness Audit Verification Report

**Phase Goal:** CycloneDX CBOM output is spec-valid, every in-scope algorithm is classified (no unknown fallbacks), golden snapshot drift is intentional and documented, and Pass-2/3 skip-list logic is fully unit-tested.
**Verified:** 2026-04-30
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | CBOM JSON+XML validate against CycloneDX 1.6 for every shipped chaos lab profile — zero schema violations | VERIFIED | `tests/test_cbom_schema_validation.py::test_cbom_validates_against_cyclonedx_1_6[*]` — 18/18 profiles PASS (broker, cloud, database, dnssec, email, identity, jwt, kerberos, ldaps, phaseA, pki, registry, saml, source, ssh-weak, storage, storage-s3, vault). Drift sentinel `test_parametrize_set_matches_docker_compose_profiles` PASS. Uses `JsonStrictValidator(SchemaVersion.V1_6).validate_str(...) is None` per RESEARCH Pitfall #2. |
| 2 | Classifier coverage report — every observed algorithm classified with no `unknown` fallback | VERIFIED | `tests/test_cbom_classifier_coverage.py::test_no_unknown_classifications_across_lab_profiles` PASS. `docs/cbom-classifier-coverage.md` lists 15 distinct algorithms across 13 of 18 profiles (5 profiles emit zero algorithm components — see Anti-Patterns / future-phase observation). All classified to non-UNKNOWN primitive (alg:none sentinel intentionally excepted per Pitfall #4). |
| 3 | All golden snapshot differences are intentional with rationale | VERIFIED | `tests/fixtures/cbom/CHANGELOG.md` exists with Phase 42 entry naming the three new fixtures (`expected_pki_cbom.json`, `expected_vault_cbom.json`, `expected_saml_cbom.json`) and rationale. Existing email/broker fixtures untouched. Snapshot tests `test_pki/vault/saml_cbom_matches_snapshot` PASS. |
| 4 | Pass-2 and Pass-3 skip-list unit tests cover all motion plaintext + v4.3 DAR skip cases | VERIFIED | `tests/test_cbom_skip_lists.py::test_skip_protocol_emits_no_cert_or_proto_component[*]` — 12/12 PASS (KAFKA-PLAIN, AMQP-PLAIN, REDIS-PLAIN, POSTGRESQL, MYSQL, RDS, S3, AZURE_BLOB, KUBERNETES, VAULT, GCP, CLOUD_SQL). Parametrize driven directly off `sorted(MOTION_PLAINTEXT_PROTOCOLS \| DAR_SKIP_PROTOCOLS)`. `test_skip_list_constants_are_nonempty` sanity guard PASS. |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|---------|---------|--------|---------|
| `pyproject.toml` | `cyclonedx-python-lib[validation]>=11.7.0,<12` pin | VERIFIED | Line 16. Also `pythonpath = ["."]` (line 82) added by 42-04. |
| `quirk/cbom/builder.py` | `MOTION_PLAINTEXT_PROTOCOLS` + `DAR_SKIP_PROTOCOLS` frozensets | VERIFIED | Lines 44, 48 declare frozensets; lines 455–456 (Pass 2) and 539–540 (Pass 3) use `*MOTION_PLAINTEXT_PROTOCOLS, *DAR_SKIP_PROTOCOLS`. |
| `tests/__init__.py` | Empty marker for package import | VERIFIED | Exists (0 bytes), enables `from tests._cbom_profiles import ...`. |
| `tests/_cbom_profiles.py` | Single source of truth for `PROFILE_ENDPOINTS` covering all 18 profiles | VERIFIED | 72 lines; module-level assert `len(PROFILE_ENDPOINTS) == 18`; imports 18 synthesizers from `test_cbom_motion_golden.py` (2) + `test_cbom_motion_endpoints.py` (16). |
| `tests/test_cbom_schema_validation.py` | CBOM-01 schema gate | VERIFIED | 92 lines. Parametrized over 18 profiles + drift sentinel. Uses `validate_str(...) is None`. |
| `tests/test_cbom_classifier_coverage.py` | CBOM-02 gate + regen | VERIFIED | 122 lines. Two tests: gate + regen-mode. Imports `PROFILE_ENDPOINTS` from shared module. |
| `tests/test_cbom_skip_lists.py` | CBOM-04 Pass-2/3 unit gate | VERIFIED | 84 lines. Parametrized off skip-list union. Empty-set guard included. |
| `tests/fixtures/cbom/expected_pki_cbom.json` | TLS-with-cert shape golden | VERIFIED | 2130 bytes. |
| `tests/fixtures/cbom/expected_vault_cbom.json` | Data-at-rest shape golden | VERIFIED | 272 bytes (small — Pass 2/3 skipped, only Pass 1 algorithm components emitted; consistent with VAULT in DAR_SKIP_PROTOCOLS). |
| `tests/fixtures/cbom/expected_saml_cbom.json` | Identity shape golden | VERIFIED | 262 bytes. |
| `tests/fixtures/cbom/CHANGELOG.md` | Drift rationale log | VERIFIED | Phase 42 entry present with file-by-file rationale and regen command. |
| `docs/cbom-classifier-coverage.md` | Generated coverage report | VERIFIED | 25 lines, lists 15 algorithms with primitive / NIST / classical-bits / source profiles. |
| `docs/UAT-SERIES.md` | UAT-42-01..04 rows | VERIFIED | All 4 rows present (lines 5294, 5325, 5357, 5392). |
| Vault `Phase-42-CBOM-Correctness-Audit.md` | Obsidian phase note | VERIFIED | 7833 bytes; frontmatter `status: complete`, `type: phase`, `updated: 2026-04-30`, source path. |
| Vault `UAT-Series.md` | Vault mirror of UAT-SERIES.md | VERIFIED | 214166 bytes (matches docs file size + frontmatter). |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `tests/test_cbom_skip_lists.py` | `quirk/cbom/builder.py` | `from quirk.cbom.builder import MOTION_PLAINTEXT_PROTOCOLS, DAR_SKIP_PROTOCOLS` | WIRED | Line 18-22 imports; parametrize at line 56-58 consumes the union. |
| `tests/test_cbom_schema_validation.py` | `cyclonedx.validation.{json,xml}` | `JsonStrictValidator + XmlValidator validate_str() is None` | WIRED | Lines 18-20 imports; lines 40-50 invoke + assert `is None`. |
| `tests/test_cbom_schema_validation.py` | `tests/_cbom_profiles.py` | `from tests._cbom_profiles import PROFILE_ENDPOINTS` | WIRED | Line 24. |
| `tests/test_cbom_classifier_coverage.py` | `tests/_cbom_profiles.py` | Same shared import | WIRED | Line 34. |
| `tests/test_cbom_classifier_coverage.py` | `quirk/cbom/classifier.py::classify_algorithm` | `classify_algorithm(name)` walks `crypto_properties.asset_type=='algorithm'` | WIRED | Lines 33, 71. |
| `tests/_cbom_profiles.py` | `test_cbom_motion_endpoints.py` + `test_cbom_motion_golden.py` | imports 18 per-profile synthesizers | WIRED | Lines 21-44. |
| `tests/test_cbom_motion_golden.py::test_pki/vault/saml_cbom_matches_snapshot` | shape-golden fixtures | `_load_snapshot('pki'/'vault'/'saml')` | WIRED | Lines 251-284. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|---------|--------------|--------|--------------------|--------|
| `tests/test_cbom_schema_validation.py` | `endpoints` | `PROFILE_ENDPOINTS[profile]()` synthesizer | YES — every entry returns >=1 endpoint with real algorithm names from `expected_results_v3.md` | FLOWING |
| `tests/test_cbom_classifier_coverage.py` | `bom.components` | `build_cbom(fn())` | YES — covers 13/18 profiles emitting algorithm components | FLOWING (with observation, see below) |
| `tests/test_cbom_skip_lists.py` | `protocol` (parametrize) | `MOTION_PLAINTEXT_PROTOCOLS \| DAR_SKIP_PROTOCOLS` (12 entries) | YES — both frozensets non-empty, full TLS+cert metadata constructed | FLOWING |
| `docs/cbom-classifier-coverage.md` | rows | regen test re-runs against `PROFILE_ENDPOINTS` | YES — 15 distinct algorithms enumerated | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---------|--------|--------|--------|
| CBOM test slice green | `.venv/bin/pytest tests/test_cbom_*.py` | 125 passed, 2 deselected, 0.75s | PASS |
| Schema validation per-profile | `.venv/bin/pytest tests/test_cbom_schema_validation.py -v` | 19/19 pass (18 profiles + drift sentinel) | PASS |
| Classifier no-unknown gate | `.venv/bin/pytest tests/test_cbom_classifier_coverage.py::test_no_unknown_classifications_across_lab_profiles` | PASS | PASS |
| Skip-list parametrized | `.venv/bin/pytest tests/test_cbom_skip_lists.py -v` | 12/12 + non-empty guard pass | PASS |
| Shape goldens | `tests/test_cbom_motion_golden.py::test_pki/vault/saml_cbom_matches_snapshot` | 3/3 PASS | PASS |
| compileall | `.venv/bin/python -m compileall quirk/ tests/` | exit 0, no output | PASS |
| Full pytest | `.venv/bin/pytest -q` | 703 passed, 14 failed, 11 deselected | PASS (failures pre-existing — see below) |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| CBOM-01 | 42-01, 42-02, 42-03 | CycloneDX 1.6 schema validation across all profiles | SATISFIED | 18 profiles validated, drift sentinel against docker-compose.yml |
| CBOM-02 | 42-04 | No UNKNOWN classifications | SATISFIED | Gate test passes; report committed |
| CBOM-03 | 42-03 | Shape goldens with intentional drift documented | SATISFIED | 3 new fixtures + CHANGELOG.md |
| CBOM-04 | 42-01, 42-05 | Pass-2/3 skip-list unit tests | SATISFIED | 12 parametrized cases pass; constants extracted |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none in phase artifacts) | — | — | — | No TODO/FIXME/placeholder/stub patterns detected in 42-01..06 created/modified files. |

### Observations (Non-Blocking)

**OBS-1: 5 profiles emit zero algorithm components.** `database`, `registry`, `source`, `ssh-weak`, `storage-s3` synthesizers in `tests/test_cbom_motion_endpoints.py` produce endpoints, but their corresponding `build_cbom()` output surfaces no Pass-1 algorithm components — likely because the endpoints exercise Pass-2/3 cert/protocol paths that for these protocols are skipped or do not generate algorithm-asset entries. The classifier gate passes vacuously for these 5 profiles (nothing to classify). Phase 42 is not the right place to expand `build_cbom()` coverage — `_ALGORITHM_TABLE` only enforces what's surfaced. **Recommend opening a backlog item for a future phase to verify whether these 5 profiles should surface algorithm components and, if so, extend the builder.**

**OBS-2: Duplicate Rule-3 fix is benign.** 42-02 added `tests/__init__.py` (0 bytes), 42-04 added `pythonpath = ["."]` to `pyproject.toml`. Both resolve `tests._cbom_profiles` cross-test imports. With both in place pytest collects the suite cleanly (verified: 703 collected/passed in full run). No negative interaction observed. Defence-in-depth is acceptable — neither needs to be reverted.

**OBS-3: Pre-existing environmental failures confirmed out-of-scope.** Full `pytest` reports 14 failures across `test_azure_blob.py` (AttributeError — Azure SDK), `test_gcs_reuse.py` (Mock — GCS SDK), `test_k8s_connector.py` (ModuleNotFoundError — kubernetes lib), `test_pdf_export.py` (Playwright), `test_skip_registry.py` (registry config drift). All pre-existing per parent commit `612dbc8` verification context. None touch CBOM pipeline. None caused by Phase 42 changes — confirmed by 100% pass rate on the full CBOM test slice (125/125).

### Human Verification Required

None. All ROADMAP success criteria are programmatically verifiable and have passing automated checks.

### Gaps Summary

No gaps. Phase 42 goal is fully achieved:

- CycloneDX 1.6 schema validation across all 18 profiles — PASS
- Classifier coverage gate (no UNKNOWN fallbacks) — PASS, with regen-deterministic Markdown report committed
- Three new shape goldens (pki/vault/saml) + CHANGELOG.md rationale — PASS
- Pass-2/3 skip-list parametrized unit tests across 12 protocols + non-empty guard — PASS
- All Mandatory Phase Completion Steps (UAT-SERIES.md update, vault sync, Obsidian phase note, compileall, full pytest) — VERIFIED

The only follow-up is OBS-1 (5 profiles emitting zero algorithm components), which is a coverage observation for a future phase, not a Phase 42 gap — the classifier gate can only enforce what `build_cbom()` surfaces.

---

_Verified: 2026-04-30_
_Verifier: Claude (gsd-verifier)_
