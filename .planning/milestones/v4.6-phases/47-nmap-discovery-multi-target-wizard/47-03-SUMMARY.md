---
phase: 47-nmap-discovery-multi-target-wizard
plan: "03"
subsystem: cbom-validation
tags: [cbom, json-validation, optional-extra, cyclonedx, tdd, uat]
dependency_graph:
  requires: ["47-02"]
  provides: ["cbom-validation hook", "json-validation extras swap"]
  affects: ["quirk/cbom/writer.py", "quirk/util/optional_extra.py", "quirk/reports/writer.py"]
tech_stack:
  added: ["cyclonedx-python-lib[json-validation]", "cbom optional-extra in pyproject.toml"]
  patterns: ["soft-fail advisory finding", "optional-extra always-probe pattern (Phase 45)", "TDD RED/GREEN cycle", "keyword-only param for backward compat"]
key_files:
  created:
    - tests/test_cbom_writer_validation.py
  modified:
    - pyproject.toml
    - quirk/util/optional_extra.py
    - quirk/cbom/writer.py
    - quirk/reports/writer.py
    - run_scan.py
    - tests/test_optional_extra.py
    - docs/UAT-SERIES.md
decisions:
  - "D-13: replaced cyclonedx-python-lib[validation] with [json-validation] in pyproject.toml; pin window >=11.7.0,<12 unchanged"
  - "D-14: validation runs AFTER output_to_file; CBOM file is NOT deleted on schema failure"
  - "D-15: schema violation emits one coverage_gap WARN finding; scan continues (soft-fail)"
  - "D-16: MissingOptionalDependencyException caught silently in writer; registry probe handles INFO advisory"
  - "RESEARCH F6 enforced: both JsonStrictValidator() constructor AND validate_str() wrapped in ONE try-except block"
  - "keyword-only error_endpoints param preserves backward compat for all positional callers in test_cbom_writer.py"
  - "Chose to extend test_cbom_schema_validation.py note rather than duplicate: new file test_cbom_writer_validation.py covers writer-level soft-fail mechanism (different concern from schema-validity of chaos-lab CBOMs)"
metrics:
  duration: "~35 minutes"
  completed: "2026-05-04"
  tasks_completed: 4
  files_modified: 7
  files_created: 1
  tests_added: 7
---

# Phase 47 Plan 03: CBOM JSON Validation + Extras Swap Summary

Post-write CycloneDX JSON schema validation with soft-fail finding emission and cyclonedx-python-lib[json-validation] extras swap.

## What Was Built

### Task 1: pyproject.toml extras swap + cbom optional-extra registry entry

**Commit:** 037051d

**pyproject.toml one-line diff:**
```diff
-    "cyclonedx-python-lib[validation]>=11.7.0,<12",
+    "cyclonedx-python-lib[json-validation]>=11.7.0,<12",
```

Added `cbom` extra to `[project.optional-dependencies]`:
```toml
cbom = ["cyclonedx-python-lib[json-validation]>=11.7.0,<12"]
```

Added `quirk[cbom]` to the `[all]` meta-extra so `pip install quirk[all]` continues to be the one-stop install.

**New REGISTRY entry in `quirk/util/optional_extra.py`:**
```python
OptionalExtra(
    extra="cbom",
    modules=("jsonschema", "referencing"),
    scanner_label="cbom_validator",
    install_hint="CBOM JSON schema validation skipped — run `pip install quirk[cbom]` to enable",
    enabled_attrs=(),  # always probe — CBOM is always written
),
```

Uses `enabled_attrs=()` (the "always probe" pattern matching the `dashboard` entry) because CBOM is emitted on every scan regardless of scanner flags.

**New optional-extra tests (2):**
- `test_cbom_registry_entry_present`: asserts modules, enabled_attrs, scanner_label, and install_hint literal.
- `test_cbom_extra_advisory_when_jsonschema_missing`: with `find_spec` patched to None → one ADVISORY appended; with modules present → no advisory.

### Task 2: Post-write JSON schema validation hook (TDD)

**Commits:** c59cf75 (RED), 1e7622d (GREEN)

**Test choice:** `tests/test_cbom_schema_validation.py` covers chaos-lab-profile schema validity (a different concern). The new file `tests/test_cbom_writer_validation.py` covers the writer-level soft-fail mechanism — correct separation of concerns.

**Signature change (keyword-only via `*`):**
```python
def write_cbom_files(
    bom: Bom,
    outdir: str,
    stamp: str,
    *,
    error_endpoints: Optional[list] = None,
) -> tuple[str, str]:
```

Keyword-only via `*` so all six positional call sites in `tests/test_cbom_writer.py` remain unchanged.

**Validation hook (inserted after JSON `output_to_file`, before XML write):**

Per RESEARCH F6 (critical): `MissingOptionalDependencyException` can fire at BOTH `JsonStrictValidator(SchemaVersion.V1_6)` constructor AND at `.validate_str()`. Both are wrapped in ONE try-except block:

```python
try:
    with open(json_path, "r", encoding="utf-8") as fh:
        json_text = fh.read()
    validator = JsonStrictValidator(SchemaVersion.V1_6)  # may raise
    err = validator.validate_str(json_text)               # may also raise
    if err is not None and error_endpoints is not None:
        from quirk.models import CryptoEndpoint
        error_endpoints.append(
            CryptoEndpoint(
                host="cbom_validator",
                port=0,
                protocol="ADVISORY",
                scan_error=f"CBOM JSON failed schema validation: {err}",
                scan_error_category="coverage_gap",
            )
        )
except MissingOptionalDependencyException:
    pass  # D-16: registry probe handles INFO advisory
```

**D-14 invariant**: the file is NOT deleted on failure — `output_to_file` runs first, validation runs after, and there is no `os.remove` on the failure branch.

**Thread-through:**
- `quirk/reports/writer.py`: added `*, error_endpoints=None` to `write_reports` signature; passes it to `write_cbom_files`.
- `run_scan.py:1002`: updated call to `write_reports(..., error_endpoints=error_endpoints)`.

**New validation tests (5):**
- `test_valid_cbom_passes_validation_no_finding`: happy path, no advisory.
- `test_invalid_cbom_emits_warn_finding_and_preserves_file`: D-14 + D-15 soft-fail with mocked validator.
- `test_missing_jsonschema_emits_no_finding_from_writer`: D-16 — validate_str raises, writer catches silently.
- `test_missing_jsonschema_at_constructor_silent`: RESEARCH F6 — constructor raises, same silent path.
- `test_error_endpoints_default_none_no_emit`: backward compat without kwarg.

### Task 3: docs/UAT-SERIES.md Phase 47 acceptance text

**Commit:** fb129de

Added Series 16: Nmap Discovery, Multi-Target Wizard & CBOM JSON Validation with 8 test cases (UAT-47-01..08):
- UAT-47-01: CSV targets through wizard (MULTI-01)
- UAT-47-02: @file targets ingestion with comment stripping (MULTI-02)
- UAT-47-03: --targets-file non-interactive run replaces config targets (MULTI-03)
- UAT-47-04: wizard nmap y/N prompt appears exactly once (DISCOVER-01)
- UAT-47-05: missing nmap binary — no crash, ADVISORY row, consulting-ports fallback (DISCOVER-02)
- UAT-47-06: probe-budget confirm prompt at targets × ports > 10,000 (DISCOVER-04)
- UAT-47-07: CBOM JSON post-write schema validation; bad CBOM yields coverage_gap WARN (D-13..D-16)
- UAT-47-08: pip install quirk[cbom] install hint actionable (D-16)

`Last Updated` bumped to 2026-05-04.

**Hand-off note:** The Obsidian vault sync of `docs/UAT-SERIES.md` (CLAUDE.md Mandatory Phase Completion Steps §3) and the `gsd-tools.cjs commit` invocation (§4) execute in the `/gsd-execute-phase` finalization sequence, not in this plan. This plan delivers the file content; the orchestrator delivers the vault sync.

### Task 4: Full regression sweep

771 tests pass. Two pre-existing failures excluded:
1. `tests/test_cbom_schema_validation.py` — pre-existing: `jsonschema`/`referencing` not installed in the test env under cyclonedx's search path (verified failing before this plan's changes).
2. `tests/test_v41_gap_closure.py::TestV41GapClosure::test_package_manifest_version_is_4_1_0` — pre-existing: installed egg-info reflects v4.0.0 (package not reinstalled after version bump; unrelated to this plan).

## Decision Coverage Matrix (D-13..D-16)

| Decision | Where implemented | Test coverage |
|----------|-------------------|--------------|
| D-13: [json-validation] extra | pyproject.toml core dep + `cbom` optional | `test_cbom_registry_entry_present` |
| D-14: file NOT deleted on failure | No `os.remove` in failure branch; write happens before validate | `test_invalid_cbom_emits_warn_finding_and_preserves_file` |
| D-15: coverage_gap WARN advisory | `error_endpoints.append(CryptoEndpoint(..., scan_error_category="coverage_gap"))` | `test_invalid_cbom_emits_warn_finding_and_preserves_file` |
| D-16: MissingOptionalDependencyException → silent | `except MissingOptionalDependencyException: pass` | `test_missing_jsonschema_emits_no_finding_from_writer`, `test_missing_jsonschema_at_constructor_silent` |
| RESEARCH F6: both constructor AND validate_str wrapped | single try-except around both calls | `test_missing_jsonschema_at_constructor_silent` |

## Deviations from Plan

### Auto-fixed Issues

None. Plan executed exactly as written.

### Pre-existing Issues Documented (not caused by this plan)

1. `tests/test_cbom_schema_validation.py` — all tests fail because `cyclonedx-python-lib[json-validation]` is not installed in the active test environment (the package is installed in the system Python but not in the worktree's test env). Verified failing on the base commit before any Plan 03 changes. Deferred to environment setup.

2. `tests/test_v41_gap_closure.py::test_package_manifest_version_is_4_1_0` — `importlib.metadata.version('quirk')` returns `4.0.0` because the egg-info reflects an older install. Pre-existing; not affected by Plan 03 changes.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries introduced. The `error_endpoints` list mutation is internal to the scan process. The `write_cbom_files` signature extension is backward-compatible.

## Known Stubs

None. All implementation is wired end-to-end: `run_scan.py` → `write_reports` → `write_cbom_files` → `JsonStrictValidator`.

## TDD Gate Compliance

- RED gate: `c59cf75` — `test(47-03): add failing tests for post-write CBOM JSON schema validation` (5 tests failing as expected).
- GREEN gate: `1e7622d` — `feat(47-03): post-write CBOM JSON schema validation with soft-fail finding` (all 5 tests passing).
- REFACTOR: no refactor pass needed.

## Self-Check: PASSED

Verified key files exist:
- `tests/test_cbom_writer_validation.py` — FOUND
- `quirk/cbom/writer.py` (modified) — FOUND
- `quirk/util/optional_extra.py` (modified) — FOUND
- `pyproject.toml` (modified) — FOUND
- `docs/UAT-SERIES.md` (modified) — FOUND

Verified commits exist:
- `037051d` feat(47-03): extras swap — FOUND
- `c59cf75` test(47-03): RED phase — FOUND
- `1e7622d` feat(47-03): GREEN phase — FOUND
- `fb129de` docs(47-03): UAT-SERIES.md — FOUND
