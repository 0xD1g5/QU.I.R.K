---
phase: 68
plan: "01"
subsystem: errors
tags: [error-registry, ux, operator-errors, tdd]
dependency_graph:
  requires: []
  provides: [quirk/errors.py, tests/test_errors.py]
  affects: [all future Wave 2+ call sites that import format_error]
tech_stack:
  added: []
  patterns: [frozen-dataclass-registry, format_error-wire-format]
key_files:
  created:
    - quirk/errors.py
    - tests/test_errors.py
  modified: []
decisions:
  - "Used @dataclass(frozen=True) per codebase pattern from quirk/util/optional_extra.py"
  - "36 codes registered (exceeds 28 minimum): INSTALL x10, DASHBOARD x12, SCHED x4, CBOM x1, plus 9 reserved domain slots"
  - "CATEGORY_TO_CODE contains only context-free mappings (missing_extra, coverage_gap); domain-specific exception/config dispatch deferred to render-time callers per D-04"
metrics:
  duration: "~5 minutes"
  completed: "2026-05-14"
  tasks: 2
  files: 2
---

# Phase 68 Plan 01: Error Registry Foundation Summary

**One-liner:** Canonical error registry `quirk/errors.py` with 36 QRK codes, frozen `ErrorEntry` dataclass, and `format_error()` wire-format helper — TDD RED/GREEN with 11 passing unit tests.

## What Was Built

### Task 1: quirk/errors.py

Created `quirk/errors.py` as the single source of truth for all operator-facing error codes.

**Public API:**
- `ErrorEntry` — frozen dataclass with `code`, `cause`, `fix` fields (immutable, raises `FrozenInstanceError` on mutation)
- `ERROR_REGISTRY: dict[str, ErrorEntry]` — 36 registered codes
- `CATEGORY_TO_CODE: dict[str, str]` — render-time dispatch map for scan_error_category values
- `format_error(code: str) -> str` — returns `[QRK-<code>] <cause> Fix: <fix>` or `[QRK-<code>] Unknown error code.` for unknown codes

**Codes registered per domain:**

| Domain | Codes | Count |
|--------|-------|-------|
| INSTALL | INSTALL-001..010 | 10 |
| DASHBOARD | DASHBOARD-001..012 | 12 |
| SCHED | SCHED-001..004 | 4 |
| CBOM | CBOM-001 | 1 |
| TLS (reserved) | TLS-099, TLS-002 | 2 |
| SSH (reserved) | SSH-099, SSH-001, SSH-002 | 3 |
| JWT (reserved) | JWT-099, JWT-001 | 2 |
| CLOUD (reserved) | CLOUD-099 | 1 |
| DB (reserved) | DB-099 | 1 |
| **Total** | | **36** |

### Task 2: tests/test_errors.py

Created `tests/test_errors.py` with 11 unit tests. All pass green.

**Test coverage:**
- `test_format_error_wire_format` — exact wire format for INSTALL-001
- `test_format_error_unknown_code` — fallback for BOGUS-999
- `test_format_error_all_codes_have_fix_segment` — every registered code produces compliant output
- `test_error_entry_is_frozen` — `FrozenInstanceError` on mutation attempt
- `test_registry_has_required_codes` — all 28 audit-required codes present
- `test_category_to_code_mapping` — missing_extra and coverage_gap map correctly
- `test_no_newlines_in_cause_or_fix` — one-line constraint enforced
- `test_install_004_includes_lsof_hint` — verbatim `lsof -i :8512` in fix
- `test_dashboard_010_qramm_multiplier_range` — 0.8/1.5 range in message
- `test_registry_keys_match_entry_code_field` — no key/code mismatches
- `test_category_to_code_values_are_registered` — all CATEGORY_TO_CODE values are valid registry keys

## TDD Gate Compliance

| Gate | Commit | Status |
|------|--------|--------|
| RED (test) | 4cbef68 | `test(68-01): add failing tests for error registry (RED)` |
| GREEN (implementation) | ca4907c | `feat(68-01): implement quirk/errors.py canonical error registry (GREEN)` |

Both gates present in order. No REFACTOR needed (implementation was clean on first pass).

## Commits

| Task | Hash | Message |
|------|------|---------|
| RED (tests) | 4cbef68 | test(68-01): add failing tests for error registry (RED) |
| GREEN (impl) | ca4907c | feat(68-01): implement quirk/errors.py canonical error registry (GREEN) |

## Deviations from Plan

### Minor: 11 tests vs plan's stated "10"

**Found during:** Task 2
**Issue:** The plan's `<action>` block included `test_format_error_all_codes_have_fix_segment` which iterates all registry codes, but the `<behavior>` list and acceptance criteria stated 10 tests with `grep -c 'def test_' returns 10`.
**Fix:** Kept all 11 tests as the extra test provides stronger coverage (verifies every registered code). Acceptance criteria stated `>= 9` test count, so this is within bounds.
**Files modified:** tests/test_errors.py
**Commit:** ca4907c

## Deferred Items

None — this plan is the foundation layer. Wave 2 call-site migration plans depend on this module.

## Self-Check: PASSED

- [x] `quirk/errors.py` exists at expected path
- [x] `tests/test_errors.py` exists at expected path
- [x] Commit 4cbef68 confirmed in git log (RED)
- [x] Commit ca4907c confirmed in git log (GREEN)
- [x] `python -m pytest tests/test_errors.py -x -q` → 11 passed
- [x] `python -c "from quirk.errors import format_error; print(format_error('INSTALL-004'))"` → starts with `[QRK-INSTALL-004]` and contains `lsof -i :8512`
- [x] `len(ERROR_REGISTRY)` → 36 (>= 28)
- [x] ErrorEntry is frozen (FrozenInstanceError on mutation)
